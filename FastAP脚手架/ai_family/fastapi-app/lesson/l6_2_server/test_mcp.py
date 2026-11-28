"""通过本机HTTP端点发现并调用6-2注册的商城工具，打印服务端实际返回的结果。"""
import asyncio
from fastmcp import Client


# 无输入参数；连接本机MCP服务，依次发现工具并调用，结果打印到终端，不修改商城数据。
# 连接、初始化或工具执行失败时异常向外传播，终端可查看具体错误，不打印虚构成功结果。
async def main():
    # URL指定HTTP传输；进入async with时客户端连接并完成MCP初始化，退出时关闭连接。
    # 此处Client连接的是已经运行的FastAPI服务，不是在本脚本中创建另一个商城服务器。
    async with Client("http://localhost:9091/mcp") as client:
        # list_tools发送tools/list，返回服务端登记的工具定义；查看目录不会查询订单或商品。
        tools = await client.list_tools()
        for item in tools:
            # name和inputSchema来自服务端注册信息，可核对工具名、必填字段与长度限制。
            print("工具：", item.name, "参数结构：", item.inputSchema)

        # 第一个参数对应tools/call中的name，第二个字典对应arguments；SDK组装协议请求并通过HTTP发送。
        # 服务端按名称找到@mcp.tool登记的get_order，将orderNo传入函数，再由原查询函数读取数据库。
        order = await client.call_tool("get_order", {"orderNo": "DEMO1001"})
        # content是MCP返回的内容块列表；本节服务端返回JSON文本，因此逐块打印text查看found与订单信息。
        for block in order.content:
            if block.type == "text":
                print("订单结果：", block.text)


        # 物流工具也接收订单号，不能改传运单号；这次调用会重新执行物流查询。
        logistics = await client.call_tool("get_logistics", {"orderNo": "DEMO1001"})
        for block in logistics.content:
            if block.type == "text":
                print("物流结果：", block.text)

        # 商品工具使用keyword字段；可改成演示数据中已有的商品关键词。
        products = await client.call_tool("search_products", {"keyword": "耳机"})
        for block in products.content:
            if block.type == "text":
                print("商品结果：", block.text)


# 直接运行本文件时启动异步main；导入此模块不会自动连接MCP或查询数据库。
if __name__ == "__main__":
    asyncio.run(main())