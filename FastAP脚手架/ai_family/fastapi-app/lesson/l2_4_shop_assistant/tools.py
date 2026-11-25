import json
from typing import Annotated
from pydantic import Field
from langchain_core.tools import tool
from lesson.l2_4_shop_assistant import queries


@tool("search_products")
async def search_products(keyword: Annotated[str, Field(description="商品名称关键词，例如耳机或音箱", min_length=1, max_length=100)]):
    """按商品名称关键词查询商品、价格和库存；最多返回五条。"""
    # 普通业务负责异步查库。
    result = await queries.search_products(keyword)
    # JSON 文本由框架放入工具结果消息，保留中文。
    return json.dumps(result, ensure_ascii=False)

# 工具名称与模型返回的 name 对应。
@tool("get_order")
# 输入完整订单号，异步返回订单结果的 JSON 文本。
async def get_order(orderNo: Annotated[str, Field(description="完整订单号，例如 DEMO1001", min_length=1, max_length=40)]):
    """按完整订单号查询订单状态、商品编号和数量。订单号必须来自用户或历史。"""
    # 工具参数沿用 orderNo，数据库查询函数使用 Python 命名。
    result = await queries.get_order(orderNo)
    # 未找到时明确保留 found=false。
    return json.dumps(result, ensure_ascii=False)

# 查询物流也使用订单编号。
@tool("get_logistics")
# 输入完整订单号，异步返回承运商、运单和物流结果的 JSON 文本。
async def get_logistics(orderNo: Annotated[str, Field(description="完整订单号，例如 DEMO1001", min_length=1, max_length=40)]):
    """按完整订单号查询承运商、运单号及最新物流；没有记录时返回 found=false。"""
    # 工具只查询演示数据库，不连接真实快递接口。
    result = await queries.get_logistics(orderNo)
    # 框架负责把结果按调用编号回传模型。
    return json.dumps(result, ensure_ascii=False)