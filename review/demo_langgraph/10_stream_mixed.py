"""
混合模式：实现多种流式输出模式
"""
from typing import TypedDict
from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer
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
    # llm = get_llm("qa", streaming=True)
    # await llm.ainvoke([HumanMessage(content="你好")])

    return {"docs": fake_docs}
    # return "hi"


# ──────────────────────────────────────────────────────────────
# 3、节点二：answer —— 真实 LLM 生成（token 级流式的来源）
# ──────────────────────────────────────────────────────────────
async def answer_node(state: QAState) -> dict:
    # streaming=True：打开工厂的流式开关，token 级流式（messages 模式）才有内容可推
    llm = get_llm("qa",streaming=True)
    prompt = f"用两句话向学员解释「{state['question']}」"
    resp = await llm.ainvoke([HumanMessage(content=prompt)])
    writer = get_stream_writer()
    writer(f"生成节点：生成完成")
    writer([1,2,4,5,6])
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
    # ══════════════════════════════════════════════════════════════
    # 混合模式：stream_mode 传列表，一次订阅两种流
    #        每帧变成 (模式名, 内容) 元组：
    #        messages 帧 → LLM 节点逐 token 输出（打字机）
    #        updates 帧  → 其他节点完成时才推一条（谁来了一条）
    # ══════════════════════════════════════════════════════════════
    async for chunk in graph.astream(
        # messages表示存储的是对话消息 一个列表，可以是ai
        {"question": "什么是事件循环"},
            stream_mode=["updates", "messages","custom"]
    ):
        print("每个节点返回的增量为：\n", chunk)
        # for node_name, node_output in chunk.items():
        #     print(f"  [节点 {node_name} 完成] 返回增量: {node_output}")




if __name__ == "__main__":
    asyncio.run(main())
