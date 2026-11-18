# 需求：用户的问题->start>分类 → 概念解答 → 结束
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


# 1、用state类来创建一个图构建器
from langgraph.graph import StateGraph,START,END
builder =  StateGraph(HelperState)

# 2、注册节点
builder.add_node("classify",classify_node)
builder.add_node("answer",answer_concept_node)

# 3、连接图
builder.add_edge(START,"classify")
builder.add_edge("classify","answer")
builder.add_edge("answer",END)

# 4、编译图
graph =  builder.compile()
print(graph.get_graph().draw_ascii()) # pip install grandalf

# 5、执行图
async def main():
    result =  await  graph.ainvoke({"question":"什么是概念"})
    print(result)

if __name__ == "__main__":
    import  asyncio
    asyncio.run(main())
