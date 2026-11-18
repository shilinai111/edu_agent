"""Reducer"""
from typing import TypedDict

from langgraph.constants import START,END
from langgraph.graph import StateGraph

"""默认合并规则：你返回哪个字段，就会用新值覆盖State那个字段的值，没返回的字段保持不变"""
# class S(TypedDict):
#     a:int
#     b:int
#
# def node1(state:S):
#     return {"a":20}
#
# builder = StateGraph(S)
#
# builder.add_node("n1", node1)
#
# builder.add_edge(START,"n1")
# builder.add_edge("n1",END)
#
# graph =  builder.compile()
#
# result =  graph.invoke({"a":10,"b":20})
# print(result)




"""2、消息没办法存入追加"""
# from typing import TypedDict
# from langgraph.graph import StateGraph, START, END
#
# class ChatS(TypedDict):
#     messages: list
#
# def add_one(state: ChatS) -> dict:
#     # state["messages"]+=["新消息"]
#     return {"messages": ["新消息"]}     # 想「加」一条，但默认是「覆盖」
#
# builder = StateGraph(ChatS)
# builder.add_node("n", add_one)
#
# builder.add_edge(START, "n")
# builder.add_edge("n", END)
# graph = builder.compile()
#
# # 初始已经有两条历史消息
# print(graph.invoke({"messages": ["历史1", "历史2"]}))


"""3、自定义合并规则 Reducer"""
import operator
from typing import TypedDict,Annotated
from langgraph.graph import StateGraph, START, END

# 自定义合并函数,实现列表的追加操作
def add(old,new):
    return old+new
"""
    def operator.add(old,new)
        return old+new
"""
# Annotated[数据类型,合并函数]
class ChatS(TypedDict):
    # messages: list
    messages: Annotated[list,operator.add]
    # messages: Annotated[list,add]
    query: str


def add_one(state: ChatS) -> dict:
    return {"messages": ["新消息"]}     # 想「加」一条，但默认是「覆盖」

builder = StateGraph(ChatS)
builder.add_node("n", add_one)


builder.add_edge(START, "n")
builder.add_edge("n", END)
graph = builder.compile()

# 初始已经有两条历史消息
print(graph.invoke({"messages": ["历史1", "历史2"],"query":"hi"}))

# 没有多轮记忆
print(graph.invoke({"messages": ["历史4"],"query":"hi"}))
