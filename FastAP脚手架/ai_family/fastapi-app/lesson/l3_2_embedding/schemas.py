"""校验页面提交的两段文本，向量和分数由后端真实计算。"""
from pydantic import BaseModel, Field, field_validator

# 输入两段文本，输出已校验对象；空白内容拒绝。
class EmbeddingCompareRequest(BaseModel):
    # 每段必填，最多 2000 字符，避免一次演示发送过长内容。
    firstText: str = Field(min_length=1, max_length=2000)
    # 第二段与第一段采用相同限制。
    secondText: str = Field(min_length=1, max_length=2000)

    # 同一个校验方法应用到两个字段。
    @field_validator("firstText", "secondText")
    # Pydantic 调用类方法，接收当前类和字段值。
    @classmethod
    # 输入原文，返回原文；空白内容抛出校验异常。
    def not_blank(cls, value):
        # 只检查，不偷偷改变用户输入的文本。
        if not value.strip():
            # 公共异常处理返回统一参数错误。
            raise ValueError("文本不能为空")
        # 保留原始内容。
        return value