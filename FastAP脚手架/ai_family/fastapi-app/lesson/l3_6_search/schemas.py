"""校验检索问题、TopK 与余弦阈值，供检索和回答接口复用。"""
from pydantic import BaseModel, Field, field_validator

# 输入本轮检索设置，输出通过字段校验的对象。
class RagSearchRequest(BaseModel):
    # 问题必填，最多 1000 字符，不是最多 1000 Token。
    question: str = Field(min_length=1, max_length=1000)
    # TopK 是结果条数上限，不保证一定返回这么多。
    topK: int = Field(ge=1, le=10)
    # 余弦可为负，这不是 0～100 的正确率。
    threshold: float = Field(ge=-1, le=1)

    # 对问题补充空白校验。
    @field_validator("question")
    # Pydantic 按类方法传入字段值。
    @classmethod
    # 输入原始问题，空白抛错，其他情况保留原文。
    def not_blank(cls, value):
        # 不把只有空格当成有效检索。
        if not value.strip():
            # 由公共异常处理转换为参数错误。
            raise ValueError("问题不能为空")
        # 保留用户原始表述。
        return value