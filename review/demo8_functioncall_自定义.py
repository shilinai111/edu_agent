"""
demo8：用 LangChain 实现「自定义 JSON Schema」的工具调用（Function Calling）
- 自定义 JSON Schema：手写 OpenAI function calling 规范，schema 完全由你掌控

"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from backend.core.llm_factory import get_llm

# ── 1. 工具的真实实现 + 名称 → 函数 的分发表 ─────────────────────────
def add(a: float, b: float) -> float:
    """
        将数字a与数字b相加
        Args:
            a: 第一个数字
            b: 第二个数字
    """
    return a + b

def multiply(a: float, b: float) -> float:
    """
        将数字a与数字b相乘
        Args:
            a: 第一个数字
            b: 第二个数字
    """
    return a * b

# ──2. 自定义 JSON Schema：完全手写，遵循 OpenAI function calling 规范 ──
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",  # 函数名字
            "description": "计算两个数字的和（加法）", # 函数描述
            "parameters": {
                "type": "object",
                "properties": { # 参数属性
                    "a": {"type": "number", "description": "第一个加数"},
                    "b": {"type": "number", "description": "第二个加数"},
                },
                "required": ["a", "b"], # 必填的参数
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",  # 函数名字
            "description": "计算两个数字的乘法",  # 函数描述
            "parameters": {
                "type": "object",
                "properties": {  # 参数属性
                    "a": {"type": "number", "description": "第一个乘数"},
                    "b": {"type": "number", "description": "第二个乘数"},
                },
                "required": ["a", "b"],  # 必填的参数
            },
        },
    },

]


def execute_tool_calls(tool_calls: list) -> list[ToolMessage]:
    TOOL_MAP = {"add": add, "multiply": multiply}
    """执行模型请求的全部 tool_calls，返回可回传给模型的 ToolMessage"""
    tool_messages = []
    for call in tool_calls:
        name, args = call["name"], call["args"]
        result = TOOL_MAP[name](**args)
        print(f"  [执行工具] {name}{args} = {result}")
        tool_messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return tool_messages


def main():
    llm = get_llm("qa")                         # 从 .env.local 读 key，走项目统一入口
    # 3、创建模型并绑定工具
    llm_with_tools = llm.bind_tools(TOOLS)      # 把手写的 JSON Schema 绑定给模型
    # 存储每一轮的对话消息
    messages = [
        SystemMessage(content="你是计算助手，遇到算术必须调用工具，不要自己心算。"),
        # HumanMessage(content="帮我计算：(12 + 8) × 5，再算 7 × 6"),
        HumanMessage(content="帮我计算：(12 + 8)*5"),
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
