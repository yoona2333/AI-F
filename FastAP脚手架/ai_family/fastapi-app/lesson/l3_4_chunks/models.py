"""映射已执行 SQL 创建的 rag_chunk，保存片段与可选向量信息。"""
from tortoise import fields, models

# ORM 将一条片段记录映射成对象，序号与数据库主键不是一回事。
class RagChunk(models.Model):
    # 自增主键，重切后会变化。
    id = fields.BigIntField(primary_key=True)
    # 所属文档编号，与 rag_document.id 对应。
    document_id = fields.BigIntField()
    # 文档内阅读顺序，从 1 开始。
    chunk_index = fields.IntField()
    # 片段直接来自原文，不由模型生成。
    content = fields.TextField()
    # 未向量化时为空，保存后是数值数组的 JSON 文本。
    embedding_json = fields.TextField(null=True)
    # 模型变化后不能混用旧向量，即使维度恰好相同。
    embedding_model = fields.CharField(max_length=100, null=True)
    # 未向量化为零，本章实际使用 256 维。
    dimension = fields.IntField(default=0)

    # 无输入参数，指定数据库表映射。
    class Meta:
        # 与本节手动执行的 SQL 一致。
        table = "rag_chunk"