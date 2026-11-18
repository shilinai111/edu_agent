# -*- coding: utf-8 -*-
# 需求：LangGraph 流式输出·方法二 —— graph.astream_events(version="v2")
# 对照课件：LangGraph入门.xmind 分支十
# 项目原型：backend/api/v1/qa.py 的 chat_stream 接口（事件三分法）
#   on_chain_start      → 推进度文案（"理解问题中..."）
#   on_chat_model_stream → 取 token 逐个推（打字机）
#   on_chain_end        → 捕获节点产出的元数据
# 运行方式（在项目根目录 EduAgent_Pro 下）：
#   python demo/demo5_langgraph_StreamEvents.py

import json
import asyncio
import os
import sys

# 兼容直接命令行运行：把项目根加进 sys.path（PyCharm 里运行可自动识别，无需这步）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from langchain_core.messages import HumanMessage

from backend.core.llm_factory import get_llm  # 项目统一 LLM 入口（读 .env.local）


# ──────────────────────────────────────────────────────────────
# 1、State：mini 版答疑
# ──────────────────────────────────────────────────────────────
class QAState(TypedDict):
    question: str  # 学员的问题
    query_type: str  # classify 节点的产出：概念题 / 代码题
    answer: str  # generate 节点的产出


# ──────────────────────────────────────────────────────────────
# 2、节点一：classify —— 模拟意图分类（普通节点，只配推进度，不推 token）
# ──────────────────────────────────────────────────────────────
async def classify_node(state: QAState) -> dict:
    await asyncio.sleep(0.5)  # 模拟分类耗时
    q = state["question"]
    qtype = "代码题" if ("代码" in q or "报错" in q) else "概念题"
    return {"query_type": qtype}


# ──────────────────────────────────────────────────────────────
# 3、节点二：generate —— 真实 LLM 生成（token 级流式的来源）
#    产出里带一点"元数据"，模拟项目里 answer_mode / confidence 的捕获
# ──────────────────────────────────────────────────────────────
async def generate_node(state: QAState) -> dict:
    # 关键点①：streaming=True —— llm_factory 的开关，开了才会在事件流里吐 on_chat_model_stream
    llm = get_llm("qa", streaming=True)
    if state["query_type"] == "代码题":
        prompt = f"先给出排查思路再给示例代码，向学员解释「{state['question']}」"
    else:
        prompt = f"用两句话向学员解释「{state['question']}」"
    # 关键点①：节点内对 LLM 要用 astream()，on_chat_model_stream 事件才会逐 token 触发
    # （如果这里写 llm.ainvoke(...)，模型一次性返回，事件流里就收不到 token 了）
    answer_text = ""
    async for tok in llm.astream([HumanMessage(content=prompt)]):
        answer_text += tok.content or ""
    return {
        "answer": answer_text,
        # 顺手放几个"元数据"字段，on_chain_end 时可以捕获
        "query_type": state["query_type"],
        "confidence": 0.9,
    }


# ──────────────────────────────────────────────────────────────
# 4、建图：START → classify → generate → END
# ──────────────────────────────────────────────────────────────
builder = StateGraph(QAState)
builder.add_node("classify", classify_node)
builder.add_node("generate", generate_node)


builder.add_edge(START, "classify")
builder.add_edge("classify", "generate")
builder.add_edge("generate", END)

graph = builder.compile()


# 只有这个节点推 token（对照 qa.py 的 _GENERATE_NODES）
_GENERATE_NODES = {"generate"}

# 节点开始时推的进度文案（对照 qa.py 的 _PROGRESS_LABELS）
_PROGRESS_LABELS = {
    "classify": "理解问题中...",
    "generate": "思考中...",
}
# ──────────────────────────────────────────────────────────────
# 6、消费事件流：进度帧直接打印，token 帧拼成打字机，meta 帧收尾
# ──────────────────────────────────────────────────────────────
async def main():
    collected = {"query_type": "", "confidence": None}  # 模拟从 on_chain_end 捕获元数据
    """
       开启事件流，返回的是一个StreamEvent 字典,字段如下：
           event	事件类型，格式为 on_RunnableType_(start|stream|end) 表是哪种类型的 Runnable 组件触发了开始|流式输出|结束 事件
                       RunnableType有 chain（节点）、chat_model(对话模型)、llm、tool等
           name	参数不太重要，产生该事件的 Runnable 名称,组件名/节点名字 例如 classify / generate / chat_model / Prompt
           metadata	元数据，包含节点名、模型参数、当前第几步等信息
           data       事件内容，字段与事件类型有关

               on_chat_model_start 	模型调用开始	data["input"]，包含 messages
               on_chat_model_stream	每收到一个 token 分块	data["chunk"]，类型为 AIMessageChunk
               on_chat_model_end	模型调用完成	data["output"]，v2 中始终为简洁的 AIMessageChunk
               on_tool_start	工具开始执行	data["input"]
               on_tool_end	工具执行完成	data["output"]
               on_chain_start / on_chain_end	图节点或链开始/结束	start 含 input，end 含 output
               on_chain_stream	链产生中间流式结果	data["chunk"]

       """
    # print(graph.get_graph().draw_mermaid())
    async for event in  graph.astream_events(
        {"question":"解释一下python的垃圾回收机制"},
        version="v2"        # v2 是事件格式版本
    ):
        # 提取出事件的类型。提取出当前执行的节点名字
        evt = event["event"]
        node = event["metadata"].get("langgraph_node")


        # ── 事件①：节点开始 → 推进度文案 ──────────────────────
        # 判断当前的进入的节点是否为classify、generate节点
        if evt == "on_chain_start" and node in _PROGRESS_LABELS:
            # 取出相应的节点对应的用户回复
            print( f"progress {_PROGRESS_LABELS[node]}")

        # ── 事件②：LLM 逐 token → 打字机 ─────────────────────
        # 判断当前流式输出模型所在的节点是否为generate节点
        elif evt == "on_chat_model_stream" and node in _GENERATE_NODES:
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                print(f"{chunk.content}",end='')

        # ── 事件③：节点结束 → 捕获元数据 ─────────────────────
        # 判断当前结束的节点是否为generate节点
        elif evt == "on_chain_end" and node in _GENERATE_NODES:
            output = event["data"].get("output", {})  # 获取该节点的输出内容
            # if isinstance(output, dict):
            #     collected["query_type"] = output.get("query_type", "")
            #     collected["confidence"] = output.get("confidence")
            print("")
            print(output)


if __name__ == "__main__":
    asyncio.run(main())
