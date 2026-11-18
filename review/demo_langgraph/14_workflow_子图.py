# -*- coding: utf-8 -*-
# 需求：LangGraph 子图 Subgraph —— 图里套图
# 场景：简历审查 —— 把"PDF 处理"（抽文本 → 结构化）抽成一张子图，
#       再当作父图里的一个节点来用，最后评审落库
# 对照课件：LangGraph入门.xmind 分支八
#
# 核心就一句话：compile() 出来的图，既能自己跑，也能当节点塞进更大的图
#
# 运行方式（项目根目录下）：python demo/demo5_langgraph_子图.py

import os
import sys
from typing import TypedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, START, END


# 父子图共用同一个 State 类（课件说的"最省事的做法"）
class S(TypedDict):
    filename: str        # 简历文件名
    text:     str        # 子图的产出：抽取并结构化后的文本
    review:   str        # 父图的产出：评审结论


# ══════════════════════════════════════════════════════════════
# 第一步：先写一张子图 —— "PDF 处理"块（两个节点，模拟回复）
# ══════════════════════════════════════════════════════════════
def extract(state: S) -> dict:
    return {"text": f"从《{state['filename']}》抽出的正文文本"}


def structure(state: S) -> dict:
    return {"text": state["text"] + "（已完成结构化）"}


sub_builder = StateGraph(S)
sub_builder.add_node("extract", extract)
sub_builder.add_node("structure", structure)

sub_builder.add_edge(START, "extract")
sub_builder.add_edge("extract", "structure")
sub_builder.add_edge("structure", END)

subgraph = sub_builder.compile()        # 编译后它就是一张完整的图


# ══════════════════════════════════════════════════════════════
# 第二步：写父图 —— 子图对象直接当节点塞进去
# ══════════════════════════════════════════════════════════════
def review(state: S) -> dict:
    # 父图节点能直接读到子图写进 State 的字段
    return {"review": f"评审结论：'{state['text']}' 质量合格"}


def save(state: S) -> dict:
    print(f"[落库] {state['review']}")
    return {}


builder = StateGraph(S)
builder.add_node("pdf_process", subgraph)   # ★ 关键就这一行：子图当节点
builder.add_node("review", review)
builder.add_node("save", save)

builder.add_edge(START, "pdf_process")
builder.add_edge("pdf_process", "review")
builder.add_edge("review", "save")
builder.add_edge("save", END)

graph = builder.compile()


if __name__ == "__main__":

    print(graph.get_graph().draw_ascii())

    result = graph.invoke({"filename": "张三的简历.pdf"})
    print(f"父图最终 State: {result}")
    #
    # print()
    # print("═" * 22 + " ③ 两张图各自长什么样 " + "═" * 22)
    # print("── 子图（两个节点）──")
    # try:
    #     print(subgraph.get_graph().draw_ascii())
    # except Exception:
    #     print("（安装 grandalf 可打印图结构：pip install grandalf）")
    # print("── 父图（子图只显示为一个节点 pdf_process）──")
    # try:
    #     print(graph.get_graph().draw_ascii())
    # except Exception:
    #     print("（安装 grandalf 可打印图结构：pip install grandalf）")
