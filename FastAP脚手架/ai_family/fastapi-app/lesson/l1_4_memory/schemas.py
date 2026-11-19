
from pydantic import BaseModel, Field, field_validator
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # 校验 question 的内容，避免只输入空格也调用模型。
    @field_validator("question")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("问题不能为空")
        return value