# -*-coding:utf-8-*-
import asyncio
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
"""调用聊天模型"""
llm = init_chat_model(
    model="deepseek-ai/DeepSeek-V3",  # 模型id
    model_provider="openai",  # 模型通信协议
    api_key = "sk-psszcltfippqkmfglcaykqjyfxboskbyvqgylnpmkckqvkjm",
    base_url="https://api.siliconflow.cn/v1",
    temperature=0,  # 不要随意发挥
    extra_body = {'thinking':{"type":"disabled"}} # 关闭模型思考能力
)
# async def main():
# result = llm.invoke("你好")
# print(result)

# asyncio.run(main())


# """调用结构化输出模型"""
# from pydantic import BaseModel, Field
# # 1、定义期望模型输出的结构
#
# class PersonInfor(BaseModel):
#     name: str = Field(description="姓名")
#     age:  int = Field(description="年龄")
#     city: str = Field(description="城市")
#
# # 2、把模型绑定上去，得到一个结构化输出的大模型
# structured_llm = llm.with_structured_output(PersonInfor,method="function_calling")
#
# # 3、调用模型。返回的是一个PersonInfor对象
# # async def main():
# result =structured_llm.invoke("我叫小花，年龄18，家在北京")
# print(result)
# print(type(result))
# print(result.model_dump())  # 将结果转换为字典
# result = result.model_dump()
# print(result['name'])
# print(result.city)

# asyncio.run(main())

"""流式输出"""
# async def main():
#    async for chunk in llm.astream("输出二郎神眼保健操"):
#        print(chunk.content, end='')
#    # result =  await  llm.astream("你好")
#    # print(result.content)
#
# asyncio.run(main())
while True:
    user = input("\n你好：")
    for chunk in llm.stream(user):
        #取消print换行
        print(chunk.content,end=' ')






