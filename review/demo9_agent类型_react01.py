"""
demo9：用 LangGraph 图实现 ReAct 循环
图结构：START → agent ⇄ tools → END
"""
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, MessagesState,END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver

from backend.core.llm_factory import get_llm

@tool
def add(a: float, b: float) -> float:
    """计算两个数字的和（加法）

    Args:
        a: 第一个加数
        b: 第二个加数
    """
    return a + b


@tool
def multiply(a: float, b: float) -> float:
    """计算两个数字的积（乘法）

    Args:
        a: 第一个乘数
        b: 第二个乘数
    """
    return a * b


TOOLS = [add, multiply]


llm_with_tools = get_llm("qa").bind_tools(TOOLS)   # ① 自己绑工具


def agent_node(state: MessagesState):
    """模型节点：调一次 LLM，把 AIMessage 追加进 messages"""
    ai_msg = llm_with_tools.invoke(state["messages"])
    # if ai_msg.tool_calls:
    #     print("模型请求调用：", [(c["name"], c["args"]) for c in ai_msg.tool_calls])
    return {"messages": [ai_msg]}                  # ② add_messages 自动追加


def build_graph():
    builder = StateGraph(MessagesState)            # ③ 状态：messages 列表
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(TOOLS))     # ④ 替代 execute_tool_calls，自带错误处理
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        tools_condition, # 路由函数
        {"tools": "tools", "__end__": END},
    )
    builder.add_edge("tools", "agent")             # ⑥ 工具结果回流模型
    return builder.compile(checkpointer=InMemorySaver())


def main():
    graph = build_graph()
    # print(graph.get_graph().draw_mermaid())

    config = {"configurable": {"thread_id": "demo9-2"}, "recursion_limit": 10} # 最大步数
    result = graph.invoke(
        {"messages": [HumanMessage(content="帮我计算：(12 + 8) × 5，再算 7 × 6")]},
        config,
    )
    print("\n最终回答：", result["messages"])


if __name__ == "__main__":
    main()