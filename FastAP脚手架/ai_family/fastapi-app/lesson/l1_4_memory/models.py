""" MySQL 消息表映射成 Python 对象。"""
from tortoise import fields, models

# 每条记录保存一条用户发言或模型回答。
class MemoryMessage(models.Model):
    id = fields.BigIntField(primary_key=True)
    role = fields.CharField(max_length=20)
    content = fields.TextField()

    # 告诉 ORM 使用哪张已经建好的表。
    class Meta:
        # 名称必须与建表 SQL 一致。
        table = "memory_message"