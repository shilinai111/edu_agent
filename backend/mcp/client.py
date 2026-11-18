# backend/mcp/client.py

import json
from typing import Any
from urllib import request

import httpx

from backend.core.logger import get_logger

logger = get_logger(__name__)


async def call_mcp_tool(
    server_url: str,   # mcp服务端的地址
    tool_name: str,     # 工具名字
    arguments: dict[str, Any],  # 工具参数
    timeout: float = 30.0,  # 请求超时时间
) -> Any:
    """
    调用 stateless MCP Server 的单个工具。

    stateless_http=True 的 Server 每次 POST 完全自包含，无需先发 initialize 握手。

    Args:
        server_url: MCP Server 基础 URL，例如 "http://localhost:8000/mcp/kb"
        tool_name:  工具名称，与 @mcp.tool() 注册名一致
        arguments:  工具参数字典
        timeout:    请求超时（秒）

    Returns:
        工具返回值（JSON 反序列化后的 Python 对象）

    Raises:
        httpx.HTTPStatusError:  Server 返回 4xx/5xx
        ValueError:             JSON-RPC 错误（工具内部异常）
        httpx.TimeoutException: 请求超时
    """
    # 构造请求体 （要发送的数据内容）
    payload = {
        "jsonrpc": "2.0",
        "id":      1,
        "method":  "tools/call",
        "params": {
            "name":      tool_name,
            "arguments": arguments,
        },
    }

    # json_response=True 的 Server 要求客户端声明 Accept: application/json，
    # 否则 Server 返回 -32600 "Not Acceptable" 错误
    # 构造请求头
    headers = {
        "Content-Type": "application/json",  # 约束的发送的类型
        "Accept":        "application/json", # 约束接收的类型
    }

    # trust_env=False：禁止 httpx 读取 HTTP_PROXY / ALL_PROXY 等环境变量和系统代理。
    # macOS 系统代理或 PyCharm/Charles 等工具设置的代理不会排除 localhost，
    # 导致本地 MCP 调用被路由到代理后返回 502。对 localhost 的内部调用永远不需要代理。
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client: # 创建一个异步的客户端、
        # request不支持异步
        # mcp的streamHTTP 传输协议规范中默认的请求方法就是post
        resp = await client.post(f"{server_url}/mcp", json=payload, headers=headers)


        resp.raise_for_status()  # 如果响应状态码不是 200，会抛出异常

    data = resp.json() # 转为字典格式
    # print(f"data:{data}")


    # JSON-RPC 错误信封
    if "error" in data:
        raise ValueError(
            f"MCP tool '{tool_name}' error: {data['error'].get('message', str(data['error']))}"
        )

    # FastMCP 对 list[dict] 的序列化行为：
    #   - 每个 dict 单独放进一个 TextContent 条目（最常见）
    #   - 或整个列表序列化成一个 TextContent 条目（部分版本）
    # 必须遍历所有 content 条目，不能只取 content[0]，否则多条结果只返回第一条。
    # print("*"*80)
    content = data.get("result", {}).get("content", []) # 返回一个结果列表
    # print(f'content:{len(content)}')
    # print(f'content:{content[0]}')
    if not content: # 如果是个空列表，就直接返回
        return []

    items = [] # 存储多个结果
    for item in content: # 遍历每一个列表里面的元素，将结果一个一个取出来
        if not isinstance(item, dict):
            continue
        text = item.get("text", "") # 获取结果值
        if not text:
            continue
        try:
            parsed = json.loads(text) # 把json字符串转换成python对象
            # print(f'parsed:{parsed}')
            # print(f'parsed:{type(parsed)}')
            # break
        except (json.JSONDecodeError, TypeError):
            parsed = text
        if isinstance(parsed, list):
            # 整个列表在一个 TextContent 里，直接返回
            return parsed
        items.append(parsed)

    return items if items else content


async def list_mcp_tools(server_url: str, timeout: float = 10.0) -> list[dict]:
    """
    列出 MCP Server 提供的所有工具（调试 / 验证用）。

    Returns:
        工具列表，每项含 name / description / inputSchema
    """
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        resp = await client.post(f"{server_url}/mcp", json=payload, headers=headers)
        resp.raise_for_status()
    # print(f"resp.json()-->{resp.json()}")
    return resp.json().get("result", {}).get("tools", [])


if __name__ =="__main__":
    import asyncio

    async def main():
        result =  await call_mcp_tool("http://127.0.0.1:8001","add",{"a":1,"b":2})
        print(result)

    asyncio.run(main())

