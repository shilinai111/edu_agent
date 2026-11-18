"""
messages 模式：只输出LLM的每个token内容
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
    #
    # llm = get_llm("qa", streaming=True)
    # await llm.ainvoke([HumanMessage(content="hi")])
    return {"docs": fake_docs}
    # return "hi"


# ──────────────────────────────────────────────────────────────
# 3、节点二：answer —— 真实 LLM 生成（token 级流式的来源）
# ──────────────────────────────────────────────────────────────
async def answer_node(state: QAState) -> dict:
    # streaming=True：打开工厂的流式开关，token 级流式（messages 模式）才有内容可推
    llm = get_llm("qa",streaming=True)
    prompt = f"用两句话向学员解释「{state['question']}」"
    # 当为流式输出时，并且模型设置streaming=True，当为ainvoke时，内部会变为流式输出LangGraph 在 callback 层
    # 挂的一个旁路监听器：它把 LLM 内部吐出的每个 token 复制一份推给你，同时 ainvoke 照常
    # 返回完整结果。两条路并行，互不干扰。
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
    async for chunk in graph.astream(
        {"question": "什么是事件循环"},
            stream_mode="messages"
    ):
        print("每个节点返回的增量为：\n", chunk)
        # for node_name, node_output in chunk.items():
        #     print(f"  [节点 {node_name} 完成] 返回增量: {node_output}")




if __name__ == "__main__":
    asyncio.run(main())
