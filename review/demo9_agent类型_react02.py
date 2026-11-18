"""
demo9：用 LangChain 高层封装实现 ReAct 循环
"""
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
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
llm = init_chat_model(
    model="deepseek-ai/DeepSeek-V3",  # 模型id
    model_provider="openai",  # 模型通信协议
    api_key = "sk-psszcltfippqkmfglcaykqjyfxboskbyvqgylnpmkckqvkjm",
    base_url="https://api.siliconflow.cn/v1",
    temperature=0,  # 不要随意发挥
    extra_body = {'thinking':{"type":"disabled"}} # 关闭模型思考能力
)

def main():
    # 得到react图
    graph = create_agent(
        model=llm,                 # 内部自动 bind_tools，不用自己绑
        tools=TOOLS,
        system_prompt="你是计算助手，遇到算术必须调用工具，不要自己心算。",
        checkpointer=InMemorySaver(),        # 多轮记忆 + 支持中断
    )
    print(graph.get_graph().draw_mermaid())

    while True:
        user = input("\nuser>")
        config = {"configurable": {"thread_id": "demo9-1"}, "recursion_limit": 10}
        result = graph.invoke(
            {"messages": [HumanMessage(content=user)]},
            config,
        )
        print(result['messages'],len(result['messages']))
        # # # print(result)
        # for m in result["messages"]:
        #     print(f"[{m.type}] {m.content or ''} {getattr(m, 'tool_calls', '')}") # 读取 tool_calls属性的值
        # print("\n最终回答：", result["messages"][-1].content)


if __name__ == "__main__":
    main()