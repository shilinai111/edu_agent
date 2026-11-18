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
# 节点函数规则：
# 第一个参数最好是state。 函数内是具体的业务代码，
# 如果需要更新字段内容需要通过去return去进行增量更新
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




# 1、用state类来创建一个图构建器
from langgraph.graph import StateGraph,START,END
builder =  StateGraph(HelperState)

# 2、注册节点
builder.add_node("classify",classify_node)
builder.add_node("concept",answer_concept_node)
builder.add_node("code2",answer_code_node)
builder.add_node("chat",answer_chat_node)

def route_by_category(state: HelperState) -> str:
    """路由函数：返回一个字符串路标，决定下一步去哪个节点"""
    return state["category"]      # 返回 "concept" / "code" / "chat"
    # return "123"     # 返回 "concept" / "code" / "chat"

# 3、连接图
builder.add_edge(START,"classify")
builder.add_conditional_edges("classify",
                              route_by_category,
                              {
                                  "concept":"concept",  # 路由函数可能返回的值：节点名字
                                  "code":"code2",
                                  "chat":"chat"
                               }
                              )



builder.add_edge("concept",END)
builder.add_edge("code2",END)
builder.add_edge("chat",END)

# 4、编译图
graph =  builder.compile()
print(graph.get_graph().draw_ascii()) # pip install grandalf

# 5、执行图
async def main():
    result =  await  graph.ainvoke({"question":"你好"})
    print(result)

if __name__ == "__main__":
    import  asyncio
    asyncio.run(main())
