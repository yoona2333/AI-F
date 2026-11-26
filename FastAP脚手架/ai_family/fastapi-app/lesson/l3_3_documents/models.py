from tortoise import fields, models


class RagDocument(models.Model):
    # 数据库生成的自增主键。
    id = fields.BigIntField(primary_key=True)
    # 仅用于展示的原文件名。
    original_name = fields.CharField(max_length=255)
    # 已校验格式：pdf、docx、md、txt。
    file_type = fields.CharField(max_length=10)
    # 服务器内部路径，不返回到前端。
    storage_path = fields.CharField(max_length=500)
    # 保存解析文本，后续切分始终以此为准。
    content = fields.TextField()
    # 0 表示未完成切分，1 表示当前片段已保存。
    chunked = fields.IntField(default=0)
    # 0 表示向量尚未全部完成，1 表示整篇已完成。
    vectorized = fields.IntField(default=0)

    # 无输入参数，指定模型与实际表的关系。
    class Meta:
        # 与手动执行的 SQL 表名一致。
        table = "rag_document"