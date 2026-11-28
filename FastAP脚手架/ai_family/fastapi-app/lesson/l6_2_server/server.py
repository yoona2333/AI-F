"""将已有商城查询函数注册到名为mall的MCP服务器，供HTTP应用处理工具发现和调用。本文件定义提供哪些工具，以及每个工具怎么执行。"""
import json
from typing import Annotated
from pydantic import Field
from fastmcp import FastMCP
from lesson.l2_4_shop_assistant import queries


# FastMCP 创建了一个服务器对象，名字叫 mall 可以把它理解成一个工具登记中心，可以按照如下结构方便理解（并非真实内部的数据结构）
# mcp
#  ├─ search_products → 对应的 Python 函数
#  ├─ get_order       → 对应的 Python 函数
#  └─ get_logistics   → 对应的 Python 函数
mcp = FastMCP("mall")

# 商品查询入口：keyword来自MCP客户端的arguments，正常返回含products的JSON字符串。
# @mcp.tool把函数登记为 MCP 工具处理函数
@mcp.tool
async def search_products(
    # keyword是客户端必须提供的字段，因为这里没有默认值；str要求文本，Annotated把类型与额外校验说明放在一起。
    # Field的min_length=1拒绝空串，max_length=100限制最多100字符；全空格仍由原查询函数检查。
    # FastMCP读取这些声明生成JSON Schema，例如properties中的keyword和required中的keyword，客户端可据此填写参数。
    keyword: Annotated[str, Field(min_length=1, max_length=100)],
) -> str:
    """按商品关键词查询商品名称、价格和库存。"""
    # FastMCP把arguments中的keyword传入这里；queries.search_products才是访问数据库的已有异步业务函数。
    # await等待查询完成后，result成为含products数组的字典；注册工具和发现目录都不会执行到这一行。
    result = await queries.search_products(keyword)
    # json.dumps把业务字典转换为字符串，ensure_ascii=False保留中文，便于客户端直接阅读JSON文本。
    # 返回后FastMCP再将这个字符串放入MCP工具结果的文本内容块；本函数不用自己拼JSON-RPC响应。
    return json.dumps(result, ensure_ascii=False)

# 订单查询入口：接收客户端arguments里的orderNo，返回found及实际订单信息；查不到时保留found=false。
# @mcp.tool将get_order登记到同一个mcp对象；下面的docstring成为客户端工具目录中的用途说明。
# 例如客户端请求name="get_order"、arguments={"orderNo":"DEMO1001"}，FastMCP按名称找到此函数并按字段传参。
@mcp.tool
async def get_order(
    # orderNo对应协议JSON的准确字段名；没有默认值所以必须提供，str表示文本，Field限制长度为1～40字符。
    # 客户端传的是订单号，不能拿物流结果中的运单号代替；参数结构检查在进入函数体前完成。
    orderNo: Annotated[str, Field(min_length=1, max_length=40)],
) -> str:
    """使用完整订单号查询订单是否存在及订单状态。"""
    # 此处把orderNo作为第一个位置参数传给queries.get_order，其形参名虽然是order_no，仍能接到同一个编号。
    # 原查询函数完成业务校验并读库，await正常返回后result才是本次查询字典；这里不调用模型。
    result = await queries.get_order(orderNo)
    # 将found和订单字段编码为JSON文本，FastMCP负责封装协议结果；found=false同样可以正常返回。
    return json.dumps(result, ensure_ascii=False)

# 物流查询入口：接收订单号，返回对应承运商、运单号与物流状态；业务异常交给FastMCP报告失败。
# @mcp.tool注册get_logistics及其参数说明，因此它也会出现在同一个服务器的tools/list结果中。
@mcp.tool
async def get_logistics(
    # orderNo与订单工具使用相同含义，无默认值表示必填；1和40分别为允许的最短、最长字符数。
    orderNo: Annotated[str, Field(min_length=1, max_length=40)],
) -> str:
    """使用订单号查询承运商、运单号、物流状态和最新事件。"""
    # FastMCP已经按字段取得订单号，这里交给已有物流查询；await等待数据库返回，未找到与查询异常分别处理。
    result = await queries.get_logistics(orderNo)
    # 返回业务结果的JSON字符串；MCP的请求编号、响应结构和HTTP写入都由框架处理。
    return json.dumps(result, ensure_ascii=False)