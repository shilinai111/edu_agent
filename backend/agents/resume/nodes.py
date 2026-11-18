# backend/agents/resume/nodes.py

import asyncio
import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text

from backend.agents.resume.state import (
    ResumeState, ResumeStructured, DimensionScore, IssueList, ResumeSummary,
)
from backend.agents.resume.prompts import (
    SYSTEM_PROMPT, EXTRACT_STRUCTURED_PROMPT, DIMENSION_REVIEW_PROMPTS,
    DIAGNOSE_ISSUES_PROMPT, GENERATE_SUMMARY_PROMPT, DIAGNOSE_THINK_PROMPT,
)
from backend.core.llm_factory import get_structured_llm, get_llm
from backend.core.logger import get_logger
from backend.dependencies import AsyncSessionLocal

logger = get_logger(__name__)


# ── 六维度定义（名称 / 权重 / 评分侧重）。权重之和 = 1.0 ──
SIX_DIMENSIONS = [
    {"key": "project_depth",  "name": "项目深度",   "weight": 0.30,
     "focus": "项目描述是否有量化数据、技术选型理由、个人贡献、难点解决"},
    {"key": "tech_match",     "name": "技术匹配度", "weight": 0.25,
     "focus": "技术栈是否与目标岗位匹配，技能描述是否有层次（熟练/了解/掌握）"},
    {"key": "expression",     "name": "表达规范性", "weight": 0.15,
     "focus": "动词开头、STAR 结构、无错别字、无主语省略歧义"},
    {"key": "structure",      "name": "简历结构",   "weight": 0.15,
     "focus": "模块完整性、排版逻辑、信息密度、重要内容是否放前面"},
    {"key": "quantification", "name": "量化程度",   "weight": 0.10,
     "focus": "性能指标、用户量、优化幅度等量化数据的使用情况"},
    {"key": "authenticity",   "name": "真实可信度", "weight": 0.05,
     "focus": "表述是否夸大、技术深度描述是否与经验年限匹配、时间线是否合理"},
]


# ── 节点①②：本地模式空跑（保留以对齐结构 / 预留对象存储扩展点）──
# "文件走对象存储"的生产架构 : 前端上传 → 存 MinIO → 后端下载 → 解析。
async def upload_to_minio_node(state: ResumeState) -> dict:
    """将文件上传到云盘用于保存文件。本项目文件已在本地，无需上传对象存储，直接跳过。"""
    logger.info("upload_to_minio.skip", review_id=state["review_id"], reason="local_mode")
    return {}


async def download_pdf_node(state: ResumeState) -> dict:
    """文件已在 pdf_local_path，无需下载，直接跳过。"""
    logger.info("download_pdf.skip", review_id=state["review_id"], reason="local_file_exists")
    return {}


# ── 节点③：extract_text —— PDF 文本提取（双栏处理 + 线程池） 非结构化文档->文本 ──
# 懒加载（Lazy Import）一些模块一启动就需要很长时间,放入函数内可以按需加载
def _sync_extract_text(pdf_path: str) -> dict:
    """同步 PDF 文本提取（线程池中运行），处理双栏布局。"""
    import fitz                                       # PyMuPDF :速度、精度
    doc = fitz.open(pdf_path)
    print("doc:",doc)
    page_count = len(doc) # 获取页面个数
    print("PDF page count:", page_count)
    all_text_parts = []  # 存储每页的内容
    for page in doc: # page为每一页的内容
        blocks = page.get_text("blocks")              # 获取每个文本块 每块 (x0,y0,x1,y1,text,no,type)
        # print("blocks:", blocks)

        text_blocks = [b for b in blocks if b[6] == 0]   # type==0 文字块,只取是文本块内容
        # print("text_blocks:", text_blocks)
        if not text_blocks:  # 简历是扫描件  都是图片直接遍历下一页
            continue
        page_width = page.rect.width # 获取页面的宽度
        # print("page_width:", page_width)
        midpoint   = page_width / 2
        # print("midpoint:", midpoint)

        left_blocks  = [b for b in text_blocks if b[0] < midpoint - 20]  # 将文本块小于midpoint - 20存储到一起
        right_blocks = [b for b in text_blocks if b[0] >= midpoint - 20] # 将文本块大于等于midpoint - 20存储到一起
        is_two_column = (
            len(left_blocks) >= 2 and len(right_blocks) >= 2    # 左边和右边的文本块数量分别大于等于2
            # max(len(text_blocks), 1) 限制范围为 1,text_blocks
            and len(right_blocks) / max(len(text_blocks), 1) > 0.3 # 右边的文本块数量除以总文本块数量大于0.3
        )
        if is_two_column:                             # 双栏：左栏读完读右栏
            left_sorted  = sorted(left_blocks,  key=lambda b: b[1]) # 基于y轴排序左边文本块
            right_sorted = sorted(right_blocks, key=lambda b: b[1]) # 基于y轴排序右边文本块
            page_text = (
                "\n".join(b[4].strip() for b in left_sorted  if b[4].strip()) # 合并左栏文本块内容
                + "\n"
                + "\n".join(b[4].strip() for b in right_sorted if b[4].strip()) # 合并右栏文本块内容
            )
        else:                                         # 单栏：按 y 从上到下
            sorted_blocks = sorted(text_blocks, key=lambda b: b[1])
            page_text = "\n".join(b[4].strip() for b in sorted_blocks if b[4].strip()) # 将列表里面的元素，通过换行符拼接成一个大字符串
        all_text_parts.append(page_text)

    doc.close()
    # 将列表中的每个元素用 "\n\n---PAGE BREAK---\n\n" 连接成一个字符串
    raw_text = "\n\n---PAGE BREAK---\n\n".join(all_text_parts)
    return {"raw_text": raw_text, "page_count": page_count}


async def extract_text_node(state: ResumeState) -> dict:
    """异步节点：线程池跑同步解析，避免阻塞事件循环。"""
    pdf_path = state["pdf_local_path"] # 获取PDF本地路径
    try:
        loop = asyncio.get_running_loop()
        # 返回pdf文本的内容与页数
        result = await loop.run_in_executor(None, _sync_extract_text, pdf_path) # 同步耗时任务需要使用run_in_executor
        raw_text, page_count = result["raw_text"], result["page_count"]
        if len(raw_text.strip()) < 200:               # 疑似扫描件/图片 PDF，仅告警
            logger.warning("extract_text.text_too_short", text_length=len(raw_text.strip()))
        logger.info("extract_text.done", page_count=page_count, text_length=len(raw_text))
        return {"raw_text": raw_text, "page_count": page_count}
    except Exception as e:
        logger.error("extract_text.failed", error=str(e))
        raise


# ── 节点④：extract_structured —— LLM 结构化提取 ──
async def extract_structured_node(state: ResumeState) -> dict:
    """用 LLM Function Calling 把文本提取成结构化简历。"""
    raw_text = state["raw_text"]  # 提取简历里面的所有文本
    text_for_llm = raw_text[:4000] if len(raw_text) > 4000 else raw_text   # 超长截断，简历不能太长
    prompt = EXTRACT_STRUCTURED_PROMPT.format(resume_text=text_for_llm)   # 通过内容格式化提示词
    structured_llm = get_structured_llm("resume", ResumeStructured)
    structured_dict = None
    for attempt in range(2):                           # 结构化输出偶发返回 None → 判空+重试
        try:
            result = await structured_llm.ainvoke([ # ResumeStructured类
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            if result is None:
                raise ValueError("structured output returned None")
            structured_dict = result.model_dump() # 转换成字典
            break
        except Exception as e:
            if attempt == 0:
                logger.warning("extract_structured.retry", error=str(e))
                await asyncio.sleep(1)
            else:
                logger.warning("extract_structured.failed", error=str(e))
    if structured_dict is None:
        structured_dict = ResumeStructured(name="未能提取").model_dump()   # 降级空结构
    logger.info("extract_structured.done",
                name=structured_dict.get("name", ""),
                projects_count=len(structured_dict.get("projects", [])))
    return {"structured": structured_dict}




# ── 节点⑤：run_six_dimensions —— 六维度并行评审 ──
async def run_six_dimensions_node(state: ResumeState) -> dict:
    """六维度并行评审：asyncio.gather 同时评，算加权综合分。"""
    raw_text   = state["raw_text"]  # 读取简历原文
    structured = state.get("structured") or {} # 读取抽取之后的结构化信息
    structured_summary = _build_structured_summary(structured) # 通过结构化信息生成摘要信息

    async def review_one_dimension(dim: dict) -> dict:
        prompt_template = DIMENSION_REVIEW_PROMPTS.get(dim["key"], "") # 根据维度key获取对应的提示词模板
        if not prompt_template:
            return _empty_dimension_score(dim)
        prompt = prompt_template.format(
            resume_text=raw_text[:3000], structured_summary=structured_summary, focus=dim["focus"],
        )
        for attempt in range(2):                      # 最多 2 次尝试
            try:
                structured_llm = get_structured_llm("resume", DimensionScore)
                result: DimensionScore = await structured_llm.ainvoke([
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ])
                d = result.model_dump() # 转成字典
                # 把该维度真实参数信息覆盖llm生成的信息，只保留分数和问题列表、建议列表
                d["dimension"], d["weight"], d["key"] = dim["name"], dim["weight"], dim["key"]
                return d
            except Exception as e:
                if attempt == 0:
                    logger.warning("six_dimensions.dimension_retry", dimension=dim["name"], error=str(e))
                    await asyncio.sleep(1)
                else:
                    logger.warning("six_dimensions.dimension_failed", dimension=dim["name"], error=str(e))
                    return _empty_dimension_score(dim)
    # 协程对象  调用协程对象 await + 协程对象
    tasks = [review_one_dimension(dim) for dim in SIX_DIMENSIONS] # 保存就是六个维度评审的协程对象/异步对象
    dimension_scores = await asyncio.gather(*tasks)              # 并行6个任务，做各个维度的评分  位置传参

    # 【76 11 2 4 6】
    weighted_score = sum(d["score"] * d["weight"] for d in dimension_scores) # 根据维度分数和权重 算出综合得分
    logger.info("six_dimensions.done", weighted_score=round(weighted_score, 2),
                scores={d["key"]: d["score"] for d in dimension_scores})
    return {"dimension_scores": list(dimension_scores), "weighted_score": round(weighted_score, 2)}


def _build_structured_summary(structured: dict) -> str:
    """把结构化数据浓缩成几行摘要，供评审使用（省 token）。"""
    lines = []
    if structured.get("name"):
        lines.append(f"姓名：{structured['name']}")
    if structured.get("target_position"):
        lines.append(f"求职意向：{structured['target_position']}")
    if structured.get("education"):
        edu = structured["education"][0] # 取最高学历
        lines.append(f"最高学历：{edu.get('school','')} {edu.get('major','')} {edu.get('degree','')}")
    if structured.get("skills_list"):
        lines.append(f"技术栈：{', '.join(structured['skills_list'][:10])}")
    if structured.get("projects"):
        proj_names = [p.get("name", "") for p in structured["projects"]] # 提取项目中所有的名字，前三个一般是重点项目
        lines.append(f"项目数量：{len(structured['projects'])} 个（{', '.join(proj_names[:3])}）")
    if structured.get("work_experience"):
        lines.append(f"工作经历：{len(structured['work_experience'])} 段")
    return "\n".join(lines) if lines else "（结构化提取失败，请基于原文评审）"


def _empty_dimension_score(dim: dict) -> dict:
    """维度评审失败时的降级结果。"""
    return {"key": dim["key"], "dimension": dim["name"], "score": 50, "weight": dim["weight"],
            "issues": ["该维度评审失败，建议人工复核"], "suggestions": []}


# ── 节点⑥：diagnose_issues —— 逐条问题诊断 ──
"""
    这段程序的核心思路是“先推理、再结构化输出、最后兜底排序”：程序先从各维度评分中汇总所有原始问题，
    形成带维度标签的问题清单；再让模型基于各维度分数和问题，先做一次低温度的宏观推理分析，
    判断问题的共性和根本原因。这个推理只作为增强信息，失败时也不影响主流程。随后把“结构化简历摘要和简历原文片段、
    原始问题清单、宏观分析”拼成提示词，交给结构化输出模型生成规范的问题条目，可包含优先级、所属维度、问题描述、
    所在位置和修改建议；宏观分析特意放在提示词末尾，贴近生成点，避免被前面的长上下文削弱，使输出更聚焦。
    如果这次结构化生成失败，就自动降级：把各维度原始问题直接转成统一中等优先级的条目，确保流程不中断。最后按高、
    中、低优先级稳定排序，把高优先级问题排到最前，并记录问题总数和高优先级问题数，便于观测。
"""
async def diagnose_issues_node(state: ResumeState) -> dict:
    """汇总维度问题 → Think 前置推理 → 结构化生成问题清单 → 按优先级排序。"""
    dimension_scores = state.get("dimension_scores", []) # 获取各个维度评分详细消息
    raw_text         = state["raw_text"]   # 获取原文档的内容
    structured       = state.get("structured") or {}  # 获取文本之后的结构化文本

    all_raw_issues = [] # 存放所有原始问题
    for dim in dimension_scores:
        for issue_text in dim.get("issues", []): # 遍历该维度的所有问题
            all_raw_issues.append(f"[{dim['dimension']}] {issue_text}")
    raw_issues_text = "\n".join(f"- {i}" for i in all_raw_issues) or "（暂无）"

    reasoning_trace = ""                              # Think 前置推理（可失败）
    try:
        dimension_scores_summary = "\n".join(
            f"- {d['dimension']}：{d['score']}分 — 问题：{', '.join(d.get('issues', [])[:2])}"
            for d in dimension_scores
        )
        think_prompt = DIAGNOSE_THINK_PROMPT.format(
            dimension_scores_summary=dimension_scores_summary, raw_issues=raw_issues_text)
        think_llm = get_llm("resume", temperature=0)
        think_resp = await think_llm.ainvoke([HumanMessage(content=think_prompt)]) # 生成的答案为该简历的宏观分析
        reasoning_trace = think_resp.content
    except Exception as e:
        logger.warning("diagnose_think.failed", error=str(e))

    think_context = f"\n\n【诊断前宏观分析】\n{reasoning_trace}" if reasoning_trace else ""

    # 提示词组成：简历摘要信息+简历原文+原始问题清单+宏观分析
    # think_context放到最后面而不是最前面的原因是出于位置效应的考虑，虽然内容放在最前面和最后面的注意力分数最高，但如果
    # 放到前面会被后面的上下文稀释掉，而放到后面是紧贴生成点，让大模型输出更聚焦
    prompt = DIAGNOSE_ISSUES_PROMPT.format(
        resume_text=raw_text[:3000],
        structured_summary=_build_structured_summary(structured),
        raw_issues=raw_issues_text,
    ) + think_context  # 上下文内容  think  回答

    try:
        structured_llm = get_structured_llm("resume", IssueList)
        result: IssueList = await structured_llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)])
        issues = [item.model_dump() for item in result.items] # 遍历每个问题条目，并把该条目转成字典格式
    except Exception as e:
        logger.warning("diagnose_issues.failed", error=str(e))
        issues = [                                    # 降级：用维度问题，统一 medium
            {"priority": "medium", "dimension": dim["dimension"], "description": issue,
             "location": "简历全文", "suggestion": "请参考评审建议修改"}
            for dim in dimension_scores for issue in dim.get("issues", [])
        ]

    priority_order = {"high": 0, "medium": 1, "low": 2}          # 按优先级排序  # obj.sort :对自身进行排序   sorted：排序完成之后返回结果
    issues.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2)) # 将优先级最高的排到最前面
    logger.info("diagnose_issues.done", total=len(issues),
                high=sum(1 for i in issues if i.get("priority") == "high"))
    return {"issues": issues}


# ── 节点⑦：generate_summary —— 整体评价 ──

"""
    整个简历审查程序本质上是一条“文档到结构化、并行评分、诊断评价、写入数据库”的处理链路：
    它先把上传的 PDF 解析成纯文本，遇到双栏排版时按左栏、右栏的顺序重排，
    避免文字串行；如果 PDF 是扫描件，只记录告警，不中断流程。然后把文本交给结构化输出模型，
    抽取姓名、学历、技能、项目、工作经历等信息，成为简历的结构化数据，并做超长截断，
    以及“判空 + 重试 + 降级空结构”的容错。接着按预先设定的六个维度（项目深度 30%、技术匹配度 25%、表达规范性 15%、简历结构 15%、
    量化程度 10%、真实可信度 5%）并发调用模型分别打分，每个维度只采信模型给出的分数、问
    题和建议，维度和权重以配置为准，最后由“分数 × 权重”累加得到综合分。再把各维度的原始问题汇总，
    先让模型做一次宏观推理分析，再把这段分析放到诊断提示词末尾，让模型深入定位每条问题的优先级（高中低）、
    所属维度和修改建议，失败时则把维度问题整体降级为中等优先级。在此基础上，结合完整的结构化信息、各维度得分与权重、
    综合分和高优先级问题，生成面向学员的整体评价（亮点、核心改进、总评、岗位匹配度）。最后把结构化数据、分数、
    问题清单、评价一起写入数据库的 JSON 字段并标记完成，任何一步写库失败都回滚。整条链路做了三层设计：
    耗时操作交给线程池，不阻塞异步事件循环；各维度并发执行，压缩总耗时；每个环节都具备重试与降级兜
    保证单点失败不拖垮整条流程，同时统一记录日志，便于观测。
"""
async def generate_summary_node(state: ResumeState) -> dict:
    """综合结构化信息、评分、问题，生成面向学员的整体评价。"""
    structured       = state.get("structured") or {}        # 简历结构化信息
    dimension_scores = state.get("dimension_scores", [])    # 各个维度评分信息
    issues           = state.get("issues", [])              # 问题清单
    weighted_score   = state.get("weighted_score", 0.0)     # 综合分数

    high_issues = [i["description"] for i in issues if i.get("priority") == "high"][:5] # 提取出高优先级的前5个问题
    high_issues_text = "\n".join(f"- {i}" for i in high_issues) or "（无高优先级问题）" # 将高优先级问题连接成字符串
    # 提取各个维度的名字，分数，权重的百分比
    scores_text = "\n".join(
        f"- {d['dimension']}：{d['score']}分（权重{int(d['weight'] * 100)}%）" for d in dimension_scores)

    prompt = GENERATE_SUMMARY_PROMPT.format(
        structured_summary=_build_structured_summary(structured),  # 简历结构化信息
        scores_summary=scores_text,   # 各个维度分数信息
        weighted_score=round(weighted_score, 1),  # 加权总分
        high_issues=high_issues_text, # 高优先级问题
        target_position=structured.get("target_position", "AI应用开发"),  # 目标岗位
    )
    structured_llm = get_structured_llm("resume", ResumeSummary)
    summary_dict = None
    for attempt in range(2):                           # 结构化输出偶发返回 None → 判空+重试
        try:
            result = await structured_llm.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)])
            if result is None:
                raise ValueError("structured output returned None")
            summary_dict = result.model_dump()  # 转成字典
            break
        except Exception as e:
            if attempt == 0:
                logger.warning("generate_summary.retry", error=str(e))
                await asyncio.sleep(1)
            else:
                logger.warning("generate_summary.failed", error=str(e))
    if summary_dict is None:
        summary_dict = {                              # 降级默认评价
            "highlights": ["简历内容已完整提交"],
            "core_improvements": high_issues[:2] if high_issues else ["请参考各维度建议修改"],
            "overall_comment": f"综合评分 {round(weighted_score, 1)} 分，请参考各维度详细反馈。",
            "fit_assessment": "与目标岗位匹配度评估暂不可用",
        }
    logger.info("generate_summary.done", highlights_count=len(summary_dict.get("highlights", [])))
    return {"summary": summary_dict}


# ── 节点⑧：save_results —— 持久化结果 ──
async def save_results_node(state: ResumeState) -> dict:
    """把完整结果写入 resume_reviews（JSONB 字段），清理临时文件。"""
    review_id = state["review_id"] # 获取到用户该次提交简历的UUID，review_id用于记录用户提交的简历信息

    # 留一份完整结果给上层（API 可直接用）
    structured_output = {
        "review_id": review_id, "student_id": state["student_id"],
        "structured": state.get("structured"),
        "weighted_score": state.get("weighted_score", 0),
        "dimension_scores": state.get("dimension_scores", []),
        "issues": state.get("issues", []),
        "summary": state.get("summary"),
    }

    async with AsyncSessionLocal() as session:        # 用统一的 SQLAlchemy 异步会话
        try:
            await session.execute(
                text("""
                    UPDATE resume_reviews
                    SET structured_data = :structured_data,
                        scores          = :scores,
                        issues          = :issues,
                        summary         = :summary,
                        status          = 'done',
                        updated_at      = NOW()
                    WHERE id = :review_id
                """),
                {
                    # JSONB 列：先 json.dumps 转 JSON 字符串；ensure_ascii=False 保留中文原文
                    "structured_data": json.dumps(state.get("structured"), ensure_ascii=False),
                    "scores": json.dumps(
                        {"dimension_scores": state.get("dimension_scores", []),
                         "weighted_score": state.get("weighted_score", 0)},
                        ensure_ascii=False),
                    "issues":  json.dumps(state.get("issues", []), ensure_ascii=False),
                    "summary": json.dumps(state.get("summary"), ensure_ascii=False),
                    "review_id": review_id,
                },
            )
            await session.commit() # 提交事务
            logger.info("save_results.db_written", review_id=review_id)
        except Exception as e:
            await session.rollback()
            logger.error("save_results.db_failed", error=str(e))
            raise

    # # 清理本地临时 PDF
    # local_path = state.get("pdf_local_path", "")
    # if local_path and os.path.exists(local_path):
    #     os.remove(local_path)
    #     logger.info("save_results.tmp_cleaned", path=local_path)

    return {"fallback_used": False, "structured_output": structured_output}


# ── 模块自测：实测 PDF 文本提取（离线；其余节点测试见各节）──
if __name__ == "__main__":
    import asyncio
    async def main():
        state = {"pdf_local_path":r"C:\Users\Administrator\Desktop\曹嘉林.pdf"}
        result =  await extract_text_node(state)
        state.update(result)
        result =  await extract_structured_node(state)
        state.update(result)
        result = await run_six_dimensions_node(state)
        state.update(result)
        result = await diagnose_issues_node(state)
        state.update(result)
        print(state)

    asyncio.run(main())
