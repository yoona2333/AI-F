from pydantic import BaseModel, Field, field_validator


class ShopChatRequest(BaseModel):

    question: str = Field(min_length=1, max_length=2000)


    @field_validator("question")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("问题不能为空")
        return value