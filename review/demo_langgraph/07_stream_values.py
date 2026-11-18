"""
values 模式：每步之后推当前完整的 State 快照，每步执行完成输出每个节点所有已经写入的state
"""
from typing import TypedDict
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from backend.core.llm_factory import get_llm
import asyncio
# ──────────────────────────────────────────────────────────────
# 1、State：和直线图 demo 一样的最小结构
# ──────────────────────────────────────────────────────────────
class QAState(TypedDict):
    question: str      # 学员的问题
    docs:      list    # 检索到的文档
    answer:    str     # 最终回答


# ──────────────────────────────────────────────────────────────
# 2、节点一：retrieve —— 模拟检索（普通节点，跑完才有产出）
# ──────────────────────────────────────────────────────────────
async def retrieve_node(state: QAState) -> dict:
    await asyncio.sleep(0.5)                           # 模拟检索耗时
    fake_docs = ["《协程入门》第3章", "《asyncio 官方文档》节选", "《事件循环笔记》"]
    return {"docs": fake_docs}
    # return "hi"


# ──────────────────────────────────────────────────────────────
# 3、节点二：answer —— 真实 LLM 生成（token 级流式的来源）
# ──────────────────────────────────────────────────────────────
async def answer_node(state: QAState) -> dict:
    llm = get_llm("qa")
    prompt = f"用两句话向学员解释「{state['question']}」"
    resp = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"answer": resp.content}


# ──────────────────────────────────────────────────────────────
# 4、建图：直线图 START → retrieve → answer → END
# ──────────────────────────────────────────────────────────────
builder = StateGraph(QAState)
builder.add_node("retrieve", retrieve_node)
builder.add_node("answer",   answer_node)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "answer")
builder.add_edge("answer", END)

graph = builder.compile()


async def main():

    print(graph.get_graph().draw_mermaid())
    #  开始流式输出
    # values 模式一开始就会推一次初始输入 State
    async for chunk in graph.astream(
        # messages表示存储的是对话消息 一个列表，可以是ai
        {"question": "什么是事件循环"},
            stream_mode="values"
    ):
        print("每个节点返回的增量为：\n", chunk)
        # for node_name, node_output in chunk.items():
        #     print(f"  [节点 {node_name} 完成] 返回增量: {node_output}")




if __name__ == "__main__":
    asyncio.run(main())
