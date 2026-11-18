"""
demo8：用 LangChain 的 @tool 装饰器实现工具调用（Function Calling）
- 装饰器方式：普通函数 + 类型注解 + docstring → 自动生成 JSON Schema（不用手写）
- 对比 demo8_functioncall_自定义.py：那边 schema 完全手写，这边全部自动生成

三个自动映射关系：
    函数名      → 工具名 name
    类型注解    → 参数的 JSON Schema
    docstring   → 工具描述 description（模型据此判断何时调用，必须写清楚）
"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from backend.core.llm_factory import get_llm
from review import demo8_functioncall_pydanticTool


# ── 1. @tool 装饰器：普通函数直接变成 LangChain 工具 ─────────────────────
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


# ──2. 通过装饰器的方式生成工具调用清单 ──
TOOLS = [demo8_functioncall_pydanticTool.add, multiply]


def execute_tool_calls(tool_calls: list) -> list[ToolMessage]:
    TOOL_MAP = {t.name: t for t in TOOLS}
    """执行模型请求的全部 tool_calls，返回可回传给模型的 ToolMessage"""
    tool_messages = []
    for call in tool_calls:
        name, args = call["name"], call["args"]
        # 装饰器工具用 .invoke() 执行：可直接吃 tool_call 字典，自动取出 args 并校验类型
        result = TOOL_MAP[name].invoke(call)
        if isinstance(result, ToolMessage):
            # 新版 LangChain：传入 tool_call 字典时，invoke 直接返回 ToolMessage（自带 tool_call_id）
            print(f"  [执行工具] {name}{args} = {result.content}")
            tool_messages.append(result)
        else:
            # 兜底：返回原始值时，手动包装成 ToolMessage 再回传给模型
            print(f"  [执行工具] {name}{args} = {result}")
            tool_messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return tool_messages


def main():
    llm = get_llm("qa")                         # 从 .env.local 读 key，走项目统一入口


    # 3、绑定工具：装饰器工具列表直接交给 bind_tools，LangChain 自动转成 OpenAI JSON Schema
    llm_with_tools = llm.bind_tools(TOOLS)

    # 存储每一轮的对话消息
    messages = [
        SystemMessage(content="你是计算助手，遇到算术必须调用工具，不要自己心算。"),
        HumanMessage(content="帮我计算：(12 + 8) × 5，再算 7 × 6"),
    ]

    for _ in range(5):                          # 最多 5 轮，防止死循环
        # 4、模型返回 tool_calls，执行本地工具，如果没有 tool_calls，则输出最终答案
        ai_msg = llm_with_tools.invoke(messages)
        messages.append(ai_msg)

        if not ai_msg.tool_calls:               # 模型不再请求工具 → 输出最终答案
            print("\n最终回答：", ai_msg.content)
            return

        print(f"模型请求调用：{[(c['name'], c['args']) for c in ai_msg.tool_calls]}")
        messages.extend(execute_tool_calls(ai_msg.tool_calls))


if __name__ == "__main__":
    main()
