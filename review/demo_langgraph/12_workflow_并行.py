# -*- coding: utf-8 -*-
# 需求：验证 LangGraph 并行化 —— 多个节点同时执行，全部跑完才继续
import asyncio
import operator
import time
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END

class S(TypedDict):
    # Reducer：并行节点写同一个字段必须"追加合并"，否则并发冲突报错
    results: Annotated[list[str], operator.add]


async def job_a(state: S) -> dict:
    print(f"  执行节点 A")
    await asyncio.sleep(1)
    return {"results": ["A的结果"]}

async def job_b(state: S) -> dict:
    print(f"  执行节点 B")
    await asyncio.sleep(2)
    return {"results": ["B的结果"]}

async def job_c(state: S) -> dict:
    print(f"  执行节点 C")
    await asyncio.sleep(1.5)
    return {"results": ["C的结果"]}

# 聚合触发时间是所有节点执行完之后才会进来
async def join(state: S) -> dict:
    print(f"  聚合节点开始执行")
    # 聚合节点：三条边同时指向它 = 必须等 A、B、C 全部跑完才会执行
    print(f"  聚合节点收到全部结果")
    return {"results": ["聚合节点的结果"]}

builder = StateGraph(S)
builder.add_node("A", job_a)
builder.add_node("B", job_b)
builder.add_node("C", job_c)
builder.add_node("join", join)


builder.add_edge(START, "A")          # START 连三条边 = 三个节点同时执行
builder.add_edge(START, "B")
builder.add_edge(START, "C")
builder.add_edge("A", "join")         # 三条边都指向 join = 全部跑完才走聚合节点
builder.add_edge("B", "join")
builder.add_edge("C", "join")
builder.add_edge("join", END)
graph = builder.compile()

async def main():
    # print(graph.get_graph().draw_mermaid()) # 输出 Mermaid 图代码
    result = await graph.ainvoke({})
    print(f"结果: {result['results']}")

if __name__ == "__main__":
    asyncio.run(main())
