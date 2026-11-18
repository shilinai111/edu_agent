"""
                    ┌──► concept ──┐
START ──► classify ─┼──► code ─────┼──► END
                    └──► chat ─────┘
              （由 route_by_category 决定走哪条）
"""
from typing import TypedDict

class HelperState(TypedDict):
    question: str      # 用户的问题（输入）
    category: str      # 分类结果：concept / code / chat（中间结果）
    answer:   str      # 最终回应（输出）

async def classify_node(state: HelperState) -> dict:
    """分类节点：根据关键词判断问题类型"""
    q = state["question"]
    if "代码" in q or "报错" in q or "bug" in q:
        category = "code"
    elif "什么是" in q or "概念" in q or "原理" in q:
        category = "concept"
    else:
        category = "chat"
    return {"category": category}          # 只返回要更新的字段


async def answer_concept_node(state: HelperState) -> dict:
    return {"answer": f"【概念解答】关于「{state['question']}」，它的核心思想是……"}

async def answer_code_node(state: HelperState) -> dict:
    return {"answer": f"【代码助手】针对「{state['question']}」，我们一步步排查……"}

async def answer_chat_node(state: HelperState) -> dict:
    return {"answer": "【闲聊】哈哈，没问题，我们继续聊～"}

from langgraph.graph import StateGraph,START,END
builder =  StateGraph(HelperState)


# 2、注册节点
builder.add_node("classify",classify_node)
builder.add_node("concept",answer_concept_node)
builder.add_node("code",answer_code_node)
builder.add_node("chat",answer_chat_node)

def route_by_category(state: HelperState) -> str:
    """路由函数：返回一个值，LangGraph 用它去映射表里查目标节点,决定下一步去哪个节点"""
    return state["category"]      # 返回 "concept" / "code" / "chat"
    # return "concept"     # 返回 "concept" / "code" / "chat"


# 3、连接图  对于条件边来说要使用add_conditional_edges添加，参数为起始节点,路由函数，映射表
builder.add_edge(START,"classify")
builder.add_conditional_edges("classify",
                              route_by_category,
                              {
                                  "concept":"concept",  # 路由函数可能返回的值：节点名字
                                  "code":"code",
                                  "chat":"chat"
                               }
                              )


builder.add_edge("concept",END)
builder.add_edge("code",END)
builder.add_edge("chat",END)


# 4、编译图
graph =  builder.compile()
print(graph.get_graph().draw_mermaid()) # 输出 Mermaid 图代码
print(graph.get_graph().draw_ascii())
# 5、执行图
async def main():
    # 执行时，需要把状态传入
    result =  await  graph.ainvoke({"question":"hi"})
    print(result)

if __name__ == "__main__":
    import  asyncio
    asyncio.run(main())