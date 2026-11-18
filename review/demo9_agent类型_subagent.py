"""
demo9：Subagents（子 Agent 当工具）
"""
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from backend.core.llm_factory import get_llm

# ① 两个子 Agent（各自独立的小图，模型/提示词互不干扰）
calc_agent = create_agent(
    model=get_llm("qa"),
    system_prompt="你是数学计算专家，负责一切算术运算，只回计算结果。",
)
writer_agent = create_agent(
    model=get_llm("qa", temperature=0.7),
    system_prompt="你是讲解老师，把给到的结论写成一句通俗的中文说明，不超过 50 字。",
)


# ② 把子 Agent 包成工具：工具函数体里就是 invoke 对应的子 Agent
@tool
def calc_expert(query: str) -> str:
    """数学计算专家：负责一切算术运算，输入用自然语言描述算式"""
    result = calc_agent.invoke({"messages": [HumanMessage(query)]})["messages"][-1].content
    return result


@tool
def writing_expert(query: str) -> str:
    """讲解专家：负责把结论或数字写成通俗的中文说明"""
    result = writer_agent.invoke({"messages": [HumanMessage(query)]})["messages"][-1].content
    return result


# ③ 主 Agent：只挂子 Agent 工具，负责分派 + 汇总
supervisor = create_agent(
    model=get_llm("qa"),
    tools=[calc_expert, writing_expert],
    system_prompt=(
        "你是调度员：算术问题交给 calc_expert，写说明交给 writing_expert，"
        "需要多个结果时依次调用，最后整合成一句完整回答。不要自己计算，也不要自己编数字。"
    ),
    checkpointer=InMemorySaver(),
)

if __name__ == "__main__":
    result = supervisor.invoke(
        {"messages": [HumanMessage("帮我算 (12 + 8) × 5 是多少，讲解一下100这个数的含义")]},
        {"configurable": {"thread_id": "demo9-3"}},
    )
    for m in result["messages"]:
        print(f"[{m.type}] {m.content or ''} {getattr(m, 'tool_calls', '')}")
    print("\n最终回答：", result["messages"][-1].content)
