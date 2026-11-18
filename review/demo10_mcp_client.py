"""
demo9：用 LangChain 高层封装实现 ReAct 循环
"""

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient

@tool
def multiply(a: float, b: float) -> float:
    """计算两个数字的积（乘法）

    Args:
        a: 第一个乘数
        b: 第二个乘数
    """
    return a * b


TOOLS = [multiply]

llm = init_chat_model(
    model="deepseek-ai/DeepSeek-V3",  # 模型id
    model_provider="openai",  # 模型通信协议
    api_key = "sk-psszcltfippqkmfglcaykqjyfxboskbyvqgylnpmkckqvkjm",
    base_url="https://api.siliconflow.cn/v1",
    temperature=0,  # 不要随意发挥
    extra_body = {'thinking':{"type":"disabled"}} # 关闭模型思考能力
)

# pip install langchain_mcp_adapters


# 自定义连接mcp服务名字，以及对应的连接信息
mcp_client =  MultiServerMCPClient(
    {
        "calc_mcp":{"url":"http://127.0.0.1:8001/mcp","transport":"streamable_http"},
        "12306-mcp": {"transport": "streamable_http","url": "https://mcp.api-inference.modelscope.net/c9f8d1c6fe6c48/mcp"}
    }
)

# 异步函数最好要在异步函数运行
# 异步函数中运行异步函数  await 协程对象
# 同步函数中运行异步函数  asynic.run(协程对象)  协程对象 = 异步函数+()
async def main():
    mcp_tools =  await  mcp_client.get_tools()
    print(mcp_tools)
    # 得到react图
    graph = create_agent(
        model=llm,                 # 内部自动 bind_tools，不用自己绑
        tools=TOOLS+mcp_tools,
        system_prompt="你是计算助手，遇到算术必须调用工具，不要自己心算。",
        checkpointer=InMemorySaver(),        # 多轮记忆 + 支持中断 保存在内存中单独存字段 开发环境放内存
        # 生产环境中最好放到mysql或者pgsql中
    )

    while True:
        user = input("\nuser>")
        #  thread_id : 区分不同会话数据
        config = {"configurable": {"thread_id": "demo9-1"}}
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=user)]},
            config,
        )
        # print(result)
        for m in result["messages"]:
            print(f"[{m.type}] {m.content or ''} {getattr(m, 'tool_calls', '')}") # 读取 tool_calls属性的值
        print("\n最终回答：", result["messages"][-1].content)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())