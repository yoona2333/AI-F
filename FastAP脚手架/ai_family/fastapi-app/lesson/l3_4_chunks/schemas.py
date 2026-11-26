"""校验窗口参数的各自范围，二者大小关系由业务补充检查。"""
from pydantic import BaseModel, Field

# 输入文档编号、窗口和重叠，输出可用于切分的参数。
class RagChunkRequest(BaseModel):
    # 必须是已经上传的正整数编号。
    documentId: int = Field(ge=1)
    # 按字符计数，不是 Token；窗口限制在 100～1000。
    chunkSize: int = Field(ge=100, le=1000)
    # 允许零重叠，另外要求小于窗口长度。
    overlap: int = Field(ge=0, le=300)