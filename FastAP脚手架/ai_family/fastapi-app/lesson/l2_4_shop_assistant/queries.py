from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.l2_4_shop_assistant.models import Product, CustomerOrder, OrderLogistics

# 在进入SQL数据库查询函数时，对输入参数进行校验
def check(value, max_length):
    """校验输入值是否为非空字符串且长度不超过最大值。"""
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        # 校验失败时不查询数据库。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "查询条件不能为空或超过长度限制")
    # 保留条件内部原文。
    return value.strip()

# 输入商品名称关键词，返回最多五个商品的字段字典。
async def search_products(keyword):
    # 先校验关键词，再通过 ORM 绑定查询参数。
    value = check(keyword, 100)
    # 名称包含关键词，按编号排序并限制条数。
    rows = await Product.filter(name__contains=value).order_by("id").limit(5)
    # 逐条转换成工具需要的数据。
    products = []
    # 每个商品保留编号、名称、两位小数价格及库存。
    for row in rows:
        # 价格用字符串表示，避免浮点展示改变金额精度。
        products.append({"id": row.id, "name": row.name, "price": format(row.price, ".2f"), "stock": row.stock})
    # 空数组表示没有匹配商品。
    return {"products": products}

# 输入完整订单号，返回 found 与可选的 order 字段。
async def get_order(order_no):
    # 查询条件按订单号字段长度校验。
    row = await CustomerOrder.filter(order_no=check(order_no, 40)).first()
    # 没有记录时明确表示未找到。
    if row is None:
        # 不编造状态或商品编号。
        return {"found": False}
    # 对外使用驼峰字段名，保留实际数据库值。
    return {"found": True, "order": {"orderNo": row.order_no, "productId": row.product_id, "quantity": row.quantity, "status": row.status}}

# 输入完整订单号，返回 found 与可选的 logistics 字段。
async def get_logistics(order_no):
    # 这里按订单编号查询，不是运单编号。
    row = await OrderLogistics.filter(order_no=check(order_no, 40)).first()
    # 未发货订单可能没有物流，不能推断成已签收。
    if row is None:
        # 没有数据时只返回查询事实。
        return {"found": False}
    # 把数据库字段映射成接口需要的驼峰名称。
    return {"found": True, "logistics": {"orderNo": row.order_no, "carrier": row.carrier, "trackingNo": row.tracking_no, "status": row.status, "latestEvent": row.latest_event}}