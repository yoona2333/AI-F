from pydantic import BaseModel, Field, field_validator

class ShopChatRequest(BaseModel):

    question: str = Field(min_length=1, max_length=2000)


    @field_validator("question")
    @classmethod
    def not_blank(cls, value):
        # 不改变原始正文中的换行。
        if not value.strip():
            # 脚手架转换为统一的参数错误响应。
            raise ValueError("问题不能为空")
        # 有效问题原样交给业务。
        return value