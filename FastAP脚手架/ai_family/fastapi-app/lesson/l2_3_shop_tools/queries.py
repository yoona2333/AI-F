"""用固定商品和订单数据实现查询，不读取数据库或真实商城。"""
from common.exception_handler import CustomException
from common.result import ResultCodeEnum


def check(value, max_length):
    # 判断是不是字符串，不是字符串或者字符串长度超过限制，或者字符串内容全是空白。
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "查询条件不能为空或超过长度限制")
    return value.strip()


# 关键词查询商品
def search_products(keyword):
    value = check(keyword, 100)
    products = [
        # 耳机有库存，用于价格和库存提问。
        {"id": 1001, "name": "声悦降噪耳机", "price": "299.90", "stock": 20},
        # 音箱无库存，不能把“存在商品”当成“有库存”。
        {"id": 1002, "name": "星空蓝牙音箱", "price": "199.00", "stock": 0},
        # 平板是另一种商品，便于核对关键词筛选。
        {"id": 1003, "name": "轻行平板", "price": "1299.00", "stock": 8},
    ]
    matches = []
    for product in products:
        if value in product["name"]:
            # 保留该商品原始字段和值。
            matches.append(product)
    # 空数组表示没有匹配商品，来源始终明确。
    return {"products": matches, "dataSource": "模拟数据，非实时商城数据"}


# 订单号查询订单
def get_order(order_no):
    value = check(order_no, 40)
    orders = {
        # 耳机订单，状态为已发货。
        "DEMO1001": {"orderNo": "DEMO1001", "productId": 1001, "quantity": 1, "status": "已发货"},
        # 音箱订单，状态为待发货。
        "DEMO1002": {"orderNo": "DEMO1002", "productId": 1002, "quantity": 1, "status": "待发货"},
    }
    order = orders.get(value)
    # 未知编号明确返回未找到。
    if order is None:
        # 同样保留模拟来源。
        return {"found": False, "dataSource": "模拟数据，非实时商城数据"}
    # 找到后返回实际固定记录。
    return {"found": True, "order": order, "dataSource": "模拟数据，非实时商城数据"}