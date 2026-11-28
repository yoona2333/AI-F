"""连接本机MCP服务，读取实际售后政策，并获取带订单号的客服任务消息。"""
import asyncio
from fastmcp import Client


# 无输入参数；依次发现资源、读取政策、发现模板和获取消息，返回内容打印到终端。
# 本脚本不调用订单工具、不请求模型；连接、资源读取或模板获取失败时异常向外传播。
async def main():
    # 进入async with时SDK连接服务端并完成MCP初始化；离开时关闭客户端连接，不关闭FastAPI服务。
    async with Client("http://localhost:9091/mcp") as client:
        # list_resources对应resources/list，只读取资源目录，不执行after_sales里的数据库查询。
        resources = await client.list_resources()
        for item in resources:
            # uri是后面读取资源使用的标识，mimeType表示资源声明的内容格式。
            print("资源：", item.name, "URI：", item.uri, "类型：", item.mimeType)

        # read_resource对应resources/read；SDK把URI交给服务端，服务端才执行after_sales查询文档原文。
        # 返回值是内容块列表，不是一个直接可用的原文字符串，所以逐项读取text。
        contents = await client.read_resource("mall://policies/after-sales")
        for item in contents:
            # 当前资源返回text/plain文本；hasattr检查块是否有text字段，避免将二进制内容块当文本读取。
            if hasattr(item, "text"):
                print("售后政策原文：")
                print(item.text)

        # list_prompts对应prompts/list，取得模板名称、说明和参数定义；此时没有生成具体任务消息。
        prompts = await client.list_prompts()
        for item in prompts:
            print("模板：", item.name, "参数：", item.arguments)

        # get_prompt对应prompts/get；第一个参数选择customer_service，第二个字典给其orderNo参数传值。
        # 服务端执行customer_service，将订单号代入文本；返回的是消息集合，不是订单查询结果。
        result = await client.get_prompt("customer_service", {"orderNo": "DEMO1001"})
        for message in result.messages:
            # role是消息角色，本节字符串模板由FastMCP转换成user消息；text是填入编号后的任务正文。
            if message.content.type == "text":
                print("消息角色：", message.role)
                print("客服任务：", message.content.text)


# 直接运行脚本时启动异步main；导入此文件不会自动连接服务端。
if __name__ == "__main__":
    asyncio.run(main())