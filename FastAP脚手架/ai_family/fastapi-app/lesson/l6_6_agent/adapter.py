"""把本轮MCP工具目录转为LangChain工具，执行时通过仍然打开的MCP连接返回观察。"""
from langchain_core.tools import StructuredTool
from fastmcp import Client
from lesson.l6_5_client.service import call_connected

# 输入协议Tool对象definition和已连接client，返回LangChain工具；工具执行异常继续向Agent传播。
def adapt(definition, client: Client):
    # 内部函数接收模型按Schema生成的参数；闭包保留当前definition与client，返回MCP真实文本结果。
    async def execute(**arguments):
        # arguments为参数字典，例如{"orderNo":"DEMO1001"}；连接必须覆盖整个Agent循环。
        return await call_connected(client, definition.name, arguments)
    # 构造模型可调用工具：名称、说明和参数结构全部来自本轮发现，查询不在这里执行。
    return StructuredTool.from_function(
        # 注册准确协议名称，模型选择后据此调用对应服务器工具。
        name=definition.name,
        # 空说明回退工具名，保证工具具有可见描述；此处不创造业务能力。
        description=definition.description or definition.name,
        # 使用服务器JSON Schema，而不是手工重复keyword/orderNo字段定义。
        args_schema=definition.input_schema,
        # 指定异步执行函数，框架await后取得观察，不调用同步函数。
        coroutine=execute,
    )