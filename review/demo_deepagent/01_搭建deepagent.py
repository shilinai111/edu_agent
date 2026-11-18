import os
# 强制清空 requests 读取的代理变量
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("NO_PROXY", None)

from typing import Literal

from deepagents import create_deep_agent
from backend.core.llm_factory import get_llm
import os
from tavily import TavilyClient
# https://app.tavily.com/home 申请apikey
os.environ["TAVILY_API_KEY"] = "tvly-1mo6lY-17qHPtaugapDll9CX7rYWAScRpdmrXd1jSaVCbKEzu"

model = get_llm("qa")
tavily_client =  TavilyClient()

def internet_search(
        query:str,
        max_result:int = 5,
        topic: Literal["general","new","finance"]  = "general",
        include_raw_content:bool = False
):
    """执行网页搜索"""
    return tavily_client.search(query=query,max_result=max_result,include_raw_content=include_raw_content,topic=topic)


# print(internet_search("牛奶是什么"))

research_instruction = """
你是一位研究专家。
"""

agent =  create_deep_agent(
    model= model,
    tools=[internet_search],
    system_prompt=research_instruction
)
# print(agent.get_graph().draw_mermaid())

# result = agent.invoke({"messages":[{"role":"user","content":"deepagent是什么"}]})
# print(result['messages'][-1].content)
# ---------------- 流式输出 ----------------
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": r"deepagent是什么"}]},
    stream_mode="updates",   # 默认就是 updates，按节点名分组
):
    # chunk 形如: {"model": {"messages": [...]}, "tools": {"messages": [...]}}
    for node_name, node_output in chunk.items():
        if not node_output or "messages" not in node_output:
            continue
        for msg in node_output["messages"]:
            # 1) 模型输出的文本增量 / 完整消息
            if msg.__class__.__name__ == "AIMessage":
                # 工具调用
                if getattr(msg, "tool_calls", None):
                    for tc in msg.tool_calls:
                        print(f"\n[工具调用] {tc['name']} args={tc['args']}")
                # 文本内容
                content = msg.content
                if isinstance(content, str) and content:
                    print(content, end="", flush=True)
                elif isinstance(content, list):  # 多模态/分段 content
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            print(part["text"], end="", flush=True)

            # 2) 工具返回结果
            elif msg.__class__.__name__ == "ToolMessage":
                print(f"\n[工具返回] {msg.name}: {str(msg.content)[:200]}...")

print()  # 收尾换行
