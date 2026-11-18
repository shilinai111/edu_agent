"""
demo8：用 Pydantic 模型定义工具参数（args_schema）实现工具调用（Function Calling）
- Pydantic 方式：先定义「参数模型」→ 再交给 @tool(args_schema=...) 绑定

三种写法对比：
    demo8_functioncall_自定义.py       手写 JSON Schema 字典（最底层，最啰嗦）
    demo8_functioncall_装饰器tool.py   类型注解 + docstring 自动生成（最省事）
    demo8_functioncall_pydanticTool.py 本文件：Pydantic 模型显式声明 schema（最可控）

适合场景：参数多、需要校验约束（ge/le）、枚举、默认值、多个工具复用同一套参数结构
"""

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from backend.core.llm_factory import get_llm


# ── 1. 用 Pydantic 模型描述参数：等价于手写 JSON Schema 的「对象版」──
# Field 的 description 会写进 schema 的 description 字段，模型靠它理解参数含义
class AddInput(BaseModel):
    """加法工具的入参"""
    a: float = Field(description="第一个加数")
    b: float = Field(description="第二个加数")


class MultiplyInput(BaseModel):
    """乘法工具的入参"""
    a: float = Field(description="第一个乘数")
    b: float = Field(description="第二个乘数")


# ── 2. @tool(args_schema=...) 把参数模型绑到工具上 ──────────────────
# 有了 args_schema：参数 schema 以它为准；函数 docstring 仍然作为工具的 description
@tool(args_schema=AddInput)
def add(a: float, b: float) -> float:
    """计算两个数字的和（加法）"""
    return a + b


@tool(args_schema=MultiplyInput)
def multiply(a: float, b: float) -> float:
    """计算两个数字的积（乘法）"""
    return a * b




TOOLS = [add, multiply]


def execute_tool_calls(tool_calls: list) -> list[ToolMessage]:
    """执行模型请求的全部 tool_calls，返回可回传给模型的 ToolMessage"""
    TOOL_MAP = {t.name: t for t in TOOLS}
    tool_messages = []
    for call in tool_calls:
        name, args = call["name"], call["args"]
        # .invoke(call)：先用 args_schema 校验参数，再把校验后的字段作为关键字参数调函数
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

    # 3、绑定工具：schema 已由 args_schema 决定，这里直接传工具对象
    llm_with_tools = llm.bind_tools(TOOLS)

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
