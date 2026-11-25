from tortoise import fields, models


class Product(models.Model):
    # 商品编号，对应主键，不由模型生成。
    id = fields.BigIntField(primary_key=True)
    # 商品显示名称。
    name = fields.CharField(max_length=100)
    # 价格保存两位小数，查询后格式化成字符串。
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    # 当前可售库存，允许为零。
    stock = fields.IntField()

    # 无输入参数，指定商品表名。
    class Meta:
        # 对应手动执行的建表 SQL。
        table = "product"


class CustomerOrder(models.Model):
    # 数据库生成的记录主键，用于 ORM 映射。
    id = fields.BigIntField(primary_key=True)
    # 业务订单号唯一，查询时必须提供完整编号。
    order_no = fields.CharField(max_length=40, unique=True)
    # 关联的商品编号，本节只读取编号。
    product_id = fields.BigIntField()
    # 购买数量。
    quantity = fields.IntField()
    # 订单状态，例如已发货、待发货。
    status = fields.CharField(max_length=30)

    # 无输入参数，指定订单表名。
    class Meta:
        # 对应已经建好的订单表。
        table = "customer_order"


class OrderLogistics(models.Model):

    id = fields.BigIntField(primary_key=True)
    # 每个订单最多一条物流记录，业务订单号不能重复。
    order_no = fields.CharField(max_length=40, unique=True)
    # 演示承运商名称。
    carrier = fields.CharField(max_length=40)
    # 运单编号，与查询条件的订单编号不同。
    tracking_no = fields.CharField(max_length=60)
    # 物流状态。
    status = fields.CharField(max_length=30)
    # 最新物流事件说明。
    latest_event = fields.CharField(max_length=200)


    class Meta:
        # ORM 不自动执行建表。
        table = "order_logistics"