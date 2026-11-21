from pydantic import BaseModel, ConfigDict, Field, field_validator


class ManualToolRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("问题不能为空")

        return value


#模型返回的参数校验
class WeatherArguments(BaseModel):
    # 拒绝 city 之外的字段，不将数字自动转换为字符串。
    model_config = ConfigDict(extra="forbid", strict=True)

    city: str = Field(min_length=1, max_length=40)

    @field_validator("city", mode="before")
    @classmethod
    def trim_city(cls, value):
        # 字符串去掉首尾空白；数字、列表和 None 不强制转成字符串。
        return value.strip() if isinstance(value, str) else value
