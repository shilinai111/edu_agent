# 需求： 可以实现解答用户的问题    用户的问题→ 概念解答 → 结束
from typing import TypedDict

# 定义图需要的字段
class HelperState(TypedDict):
    question: str      # 用户的问题（输入）
    answer:   str      # 最终回应（输出）

# 节点函数规则：
# 第一个参数最好是state。 函数内是具体的业务代码，
# 如果需要更新字段内容需要通过去return去进行增量更新，langgraph内部会自动进行字段更新
async def answer_concept_node(state: HelperState) -> dict:
    # 具体的处理逻辑
    # state["answer"] = f"【概念解答】关于「{state['question']}」，它的核心思想是……"
    return {"answer": f"【概念解答】关于「{state['question']}」，它的核心思想是……"}


# 1、用state类来创建一个图构建器
from langgraph.graph import StateGraph,START,END
builder =  StateGraph(HelperState)

# 2、注册节点  自定义节点名 具体的节点函数
builder.add_node("answer",answer_concept_node)

# 3、连接图
builder.add_edge(START,"answer")
builder.add_edge("answer",END)

# 4、编译图
graph =  builder.compile()

# 查看图结构
# print(graph.get_graph().draw_mermaid()) # 输出 Mermaid 图代码
print(graph.get_graph().draw_ascii()) # pip install grandalf

# 5、执行图
async def main():
    # 执行时，需要把状态传入
    result =  await  graph.ainvoke({"question":"什么是装饰器","answer":""})
    print(result)

if __name__ == "__main__":
    import  asyncio
    asyncio.run(main())
