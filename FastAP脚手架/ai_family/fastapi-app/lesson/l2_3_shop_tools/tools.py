import json
from typing import Annotated
from pydantic import Field
from langchain_core.tools import tool
from lesson.l2_3_shop_tools import queries


@tool("search_products")
def search_products(keyword: Annotated[str, Field(description="商品名称关键词，例如耳机或音箱", min_length=1, max_length=100)]):
    """根据关键词搜索商品，用户想要查商品的时候调用。
        Args:
            keyword: 商品搜索关键词
    """
    result = queries.search_products(keyword)
    return json.dumps(result, ensure_ascii=False)


@tool("get_order")
def get_order(orderNo: Annotated[str, Field(description="完整订单号，例如 DEMO1001", min_length=1, max_length=40)]):
    """根据订单号获取订单信息，用户想要查看订单的时候调用。
        Args:
            orderNo: 订单号
    """
    result = queries.get_order(orderNo)
    return json.dumps(result, ensure_ascii=False)