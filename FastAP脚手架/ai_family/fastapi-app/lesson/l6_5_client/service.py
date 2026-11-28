"""连接本机MCP Server，发现工具并执行手动调用；结果以文本交给调试页面。"""
from fastmcp import Client
from common.exception_handler import CustomException
from common.result import ResultCodeEnum

# 连接当前FastAPI工程的MCP端点；Client根据HTTP URL选择Streamable HTTP传输。
MCP_URL = "http://127.0.0.1:9091/mcp"

# 无参数，返回工具列表，每项包含name、description、inputSchema；连接或发现失败向HTTP异常处理传播。
async def list_tools() -> list:
    # async with建立并初始化连接，离开时关闭；不能在关闭后继续使用本次客户端。
    async with Client(MCP_URL) as client:
        # SDK执行tools/list，得到协议Tool对象列表，此操作不查询商品或订单。
        tools = await client.list_tools()
        # 每项转为页面所需字段；inputSchema原样保留，便于核对必填参数和长度限制。
        return [{"name": item.name, "description": item.description or "", "inputSchema": item.input_schema} for item in tools]

# 输入已连接client、工具名称name和参数字典arguments，返回正常工具结果的文本；协议工具错误立即抛出。
async def call_connected(client: Client, name: str, arguments: dict) -> str:
    # call_tool发送tools/call，默认raise_on_error=True，工具执行错误不会被当作正常观察返回。
    result = await client.call_tool(name, arguments)
    # 逐项读取TextContent.text，非文本项不作为本节查询正文；换行连接多个文本块，保留JSON原文。
    text = "\n".join(item.text for item in result.content if item.type == "text")
    # 当前三个查询工具均应返回文本；缺少文本时不向页面展示空的成功结果。
    if not text:
        # 此处缺少的是协议预期内容，不等同于products为空或found=false。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "MCP 工具没有返回文本结果")
    # 页面按纯文本展示；Agent也可以把此字符串作为工具观察。
    return text

# 输入name和arguments，建立一次客户端连接，确认工具存在后调用，返回含result的页面对象。
async def call_tool(name: str, arguments: dict) -> dict:
    # 连接覆盖发现与执行两个步骤，结束后自动清理HTTP会话。
    async with Client(MCP_URL) as client:
        # 读取真实目录，禁止客户端用任意函数名绕过MCP服务器注册的能力。
        tools = await client.list_tools()
        # any逐个检查工具名，至少一个相同才允许调用；不把页面提交的名称当成本地函数执行。
        if not any(item.name == name for item in tools):
            # 未注册名称直接失败，此时尚未执行工具。
            raise CustomException(ResultCodeEnum.PARAM_ERROR, "MCP 工具不存在")
        # 等待真实调用结果，返回字段result对应页面结果区。
        return {"result": await call_connected(client, name, arguments)}