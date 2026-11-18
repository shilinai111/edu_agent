# -*- coding: utf-8 -*-
# 需求：LangGraph 工作流模式⑤ 评估者-优化者 —— 生成 ↔ 评审的批改循环
# 场景：面试陪练 —— AI 先给学员写一版"面试自我介绍"（优化者），
#       评估者按明确的过关标准审稿：不达标带具体意见打回重写，达标才放行
# 对照课件：LangGraph入门.xmind 分支七 模式⑤
#
# 课件里讲的"最大的坑"也在代码里：评估者标准不明确 → 循环停不下来，
# 所以提示词里写死了 PASS 条件，另外加了 max_rounds 保险丝
#
# 运行方式（项目根目录下）：python demo/demo5_langgraph_评估者优化者.py

import asyncio
import os
import sys
from typing import TypedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, START, END

from backend.core.llm_factory import get_llm           # 项目统一 LLM 入口（读 .env.local）

MAX_ROUNDS = 3                                          # 保险丝：最多重写 3 轮


class S(TypedDict):
    draft:    str        # 当前的自我介绍草稿
    feedback: str        # 评估者的修改意见（PASS 时为空）
    round:    int        # 第几轮
    verdict:  str        # 评估结论：PASS / NEED_FIX


# ──────────────────────────────────────────────────────────────
# 节点一：优化者（生成方）—— 第一轮写初稿，之后带意见重写
# ──────────────────────────────────────────────────────────────
async def optimize(state: S) -> dict:
    llm = get_llm("qa")
    rnd = state["round"] + 1
    if rnd == 1:
        prompt = "帮学员写一段面试自我介绍，求职岗位是 Python 大模型开发。直接输出自我介绍内容。"
    else:
        prompt = (f"这是学员的面试自我介绍：\n{state['draft']}\n"
                  f"评审意见是：{state['feedback']}\n"
                  "按意见修改，直接输出修改后的全文。")
    resp = await llm.ainvoke(prompt)
    print(f"\n===== 第 {rnd} 轮：优化者交稿 =====\n{resp.content.strip()}")
    return {"draft": resp.content.strip(), "round": rnd}


# ──────────────────────────────────────────────────────────────
# 节点二：评估者（评审方）—— 按写死的过关标准审稿
# 标准：①不超过 80 字 ②提到一个具体项目 ③至少有一个数字量化
# 输出格式写死：PASS 或 NEED_FIX: 具体意见（不给意见的打回 = 甲方式"再改改"）
# ──────────────────────────────────────────────────────────────
async def evaluate(state: S) -> dict:
    llm = get_llm("qa")
    prompt = (
        "你是评审。按以下三条标准检查这段面试自我介绍：\n"
        "1. 不超过 80 字\n"
        "2. 提到了一个具体项目\n"
        "3. 至少有一个数字量化（如人数、性能提升）\n"
        "三条全满足输出：PASS\n"
        "否则输出：NEED_FIX: 具体修改意见（要具体到改什么）\n\n"
        f"自我介绍：\n{state['draft']}"
    )
    resp = await llm.ainvoke(prompt)
    text = resp.content.strip()
    verdict = "PASS" if text.startswith("PASS") else "NEED_FIX"
    print(f"----- 评估者审稿 ----- {verdict}")
    if verdict == "NEED_FIX":
        print(f"修改意见：{text}")
    return {"verdict": verdict, "feedback": text}


# ──────────────────────────────────────────────────────────────
# 路由：合格放行；不合格且没超轮数 → 打回重写；超轮数 → 强制放行兜底
# ──────────────────────────────────────────────────────────────
def route(state: S) -> str:
    if state["verdict"] == "PASS":
        return "pass"
    if state["round"] >= MAX_ROUNDS:
        print(f"\n[保险丝] 已重写 {MAX_ROUNDS} 轮仍未 PASS，强制放行，避免无限循环")
        return "pass"
    return "fix"


builder = StateGraph(S)
builder.add_node("optimize", optimize)          # 优化者：写 / 改
builder.add_node("evaluate", evaluate)          # 评估者：审

builder.add_edge(START, "optimize")
builder.add_edge("optimize", "evaluate")        # 交稿必审
builder.add_conditional_edges(
    "evaluate",                                 # 评估者后面接"回头"条件边
    route,
    {"pass": END, "fix": "optimize"},           # 不合格 → 回到优化者，形成循环
)

graph = builder.compile()


if __name__ == "__main__":
    result = asyncio.run(graph.ainvoke({
        "draft": "", "feedback": "", "round": 0, "verdict": "",
    }))
    print("\n===== 最终采用的自我介绍 =====")
    print(result["draft"])
