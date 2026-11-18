# -*- coding: utf-8 -*-
# 需求：LangGraph 工作流模式④ 编排者-工作者
# 场景：EduAgent 平台的前台调度 —— 学员一次提出多个需求，
#       编排节点（大模型）看着需求决定派给哪几个子任务节点，
#       子任务节点（试卷批改/模拟面试/简历审查）返回文字模拟回复，最后汇总
# 对照课件：LangGraph入门.xmind 分支七 模式4
#
# 运行方式（项目根目录下）：python demo/demo5_langgraph_编排者工作者LLM.py

import asyncio
import os
import sys
import operator
from typing import Annotated, TypedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send                       # Send：运行时动态派发节点

from backend.core.llm_factory import get_llm           # 项目统一 LLM 入口（读 .env.local）


class S(TypedDict):
    request: str                                       # 学员的原话
    tasks:   list[str]                                 # 编排者拆出的服务清单
    # Reducer：多个子任务节点写同一个字段，追加合并
    replies: Annotated[list[str], operator.add]#多个子任务并行写入同一个 replies 字段**时，不是覆盖，而是列表追加


# ──────────────────────────────────────────────────────────────
# 节点一：编排者（大模型）—— 看学员需求，决定这次要派哪几个服务
# ──────────────────────────────────────────────────────────────
async def orchestrator(state: S) -> dict:
    llm = get_llm("qa")
    resp = await llm.ainvoke(
        "学员在 EduAgent 平台提出了下面的需求。平台有三个服务：试卷批改、模拟面试、简历审查。\n"
        "判断这次需要提供哪几个服务，每行输出一个服务名（只能写这三个词），不要多余解释。\n"
        f"学员需求：{state['request']}"
    ) # 试卷批改   试卷批改\n模拟面试
    # 只保留合法服务名，防止模型多嘴
    services = {"试卷批改", "模拟面试", "简历审查"}
    tasks = [line.strip() for line in resp.content.splitlines() if line.strip() in services]
    print(f"[编排者(大模型)] 从学员需求里拆出 {len(tasks)} 个任务：{tasks}")
    return {"tasks": tasks}


# ──────────────────────────────────────────────────────────────
# 派活函数：编排者后面的条件边
# 清单里有几个服务就 Send 几个，派给对应的子任务节点  send(节点名字，节点输入参数)
# ──────────────────────────────────────────────────────────────
def dispatch(state: S) -> list:
    box = {"试卷批改": "grade_exam", "模拟面试": "mock_interview", "简历审查": "review_resume"}
    #第二个参数 `{}` 是传给子节点的状态（这里子任务不需要额外参数，所以传空）
    return [Send(box[t], {}) for t in state["tasks"]]   # 列表中存储 Send 对象


# ──────────────────────────────────────────────────────────────
# 三个子任务节点：各干各的活，这里用文字模拟回复（不调大模型，代码最简）
# ──────────────────────────────────────────────────────────────
def grade_exam(state: dict) -> dict:
    print("开始试卷批改")
    return {"replies": ["【试卷批改】收到试卷，正在批改，2 分钟后返回成绩单。（模拟回复）"]}


def mock_interview(state: dict) -> dict:
    print("开始模拟面试")
    return {"replies": ["【模拟面试】面试间已就位，第一题：请介绍一下你最熟的项目。（模拟回复）"]}


def review_resume(state: dict) -> dict:
    return {"replies": ["【简历审查】收到简历，六维度评分进行中，稍后给出审查报告。（模拟回复）"]}


# ──────────────────────────────────────────────────────────────
# 节点五：汇总 —— 派出去的服务全部完成才执行
# ──────────────────────────────────────────────────────────────
def collect(state: S) -> dict:
    print(f"\n[汇总] 本次共完成 {len(state['replies'])} 项服务：")
    for r in state["replies"]:
        print("  " + r)
    return {}


builder = StateGraph(S)
builder.add_node("orchestrator", orchestrator)
builder.add_node("grade_exam",     grade_exam)       # 子任务节点①：试卷批改
builder.add_node("mock_interview", mock_interview)   # 子任务节点②：模拟面试
builder.add_node("review_resume",  review_resume)    # 子任务节点③：简历审查
builder.add_node("collect", collect)

builder.add_edge(START, "orchestrator")
builder.add_conditional_edges("orchestrator", dispatch)   # 编排者后面接"派活"条件边
builder.add_edge("grade_exam",     "collect")             # 三路全部汇入 collect
builder.add_edge("mock_interview", "collect")             # = 全部完成才汇总
builder.add_edge("review_resume",  "collect")
builder.add_edge("collect", END)

graph = builder.compile()


async def main():

    await graph.ainvoke({
        "request": "帮我模拟面试一下,批改一下试卷，审查一下简历",
        "tasks": [], "replies": [],
    })



if __name__ == "__main__":
    # 两次 ainvoke 必须在同一个事件循环里（跨 asyncio.run 复用连接会报 Event loop is closed）
    asyncio.run(main())


#LangGraph 的特性：**多个边指向同一个节点，会等待所有上游分支全部跑完，才执行 collect**
# 也就是：全部子任务完成，才汇总输出。