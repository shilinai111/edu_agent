"""
demo9：用 LangChain 高层封装实现 ReAct 循环
"""
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from backend.core.llm_factory import get_llm
from langgraph.checkpoint.memory import InMemorySaver


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


def main():
    graph = create_agent(
        model=get_llm("qa"),                 # 内部自动 bind_tools，不用自己绑
        tools=TOOLS,
        system_prompt="你是计算助手，遇到算术必须调用工具，不要自己心算。",
        checkpointer=InMemorySaver(),        # 多轮记忆 + 支持中断
    )
    print(graph.get_graph().draw_mermaid())
    config = {"configurable": {"thread_id": "demo9-1"}, "recursion_limit": 10}
    result = graph.invoke(
        {"messages": [HumanMessage(content="帮我计算：(12 + 8) × 5，再算 7 × 6")]},
        config,
    )
    # print(result)
    for m in result["messages"]:
        print(f"[{m.type}] {m.content or ''} {getattr(m, 'tool_calls', '')}") # 读取 tool_calls属性的值
    print("\n最终回答：", result["messages"][-1].content)


if __name__ == "__main__":
    main()