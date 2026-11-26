"""校验按文档执行操作时提交的编号，不接收页面传来的原文。"""
from pydantic import BaseModel, Field

# 输入正整数编号，输出可用于后端查询的 documentId。
class RagDocumentRequest(BaseModel):
    # 名称与页面字段一致，最小为 1。
    documentId: int = Field(ge=1)