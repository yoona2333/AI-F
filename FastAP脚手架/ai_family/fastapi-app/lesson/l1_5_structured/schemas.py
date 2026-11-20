from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductRequest(BaseModel):

    description: str = Field(min_length=1, max_length=2000)

    @field_validator("description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        # strip 仅用于判断，不改变用户原文。
        if not value.strip():
            # Pydantic 将 ValueError 转换为字段校验错误。
            raise ValueError("商品描述不能为空")
        # 有效描述原样传给提取业务。
        return value



class ProductInfo(BaseModel):
    # forbid 表示拒绝这三个字段之外的额外字段。
    #禁止前端传模型里没有定义的字段
    model_config = ConfigDict(extra="forbid")
    brand: str | None = Field(max_length=80, description="输入明确写出的品牌，没有则为 null")
    price: Decimal | None = Field(ge=0, max_digits=10, decimal_places=2, description="人民币价格，没有则为 null")
    sellingPoints: list[str] = Field(max_length=8, description="输入明确写出的卖点，没有则为空列表")

    # 对品牌执行额外校验，null 合法，空白字符串不合法。
    @field_validator("brand")
    @classmethod
    def brand_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("品牌不能是空白字符串")
        return value

    # 检查列表中的每条卖点，而不只是列表条数。
    @field_validator("sellingPoints")
    @classmethod
    def points_not_blank(cls, values: list[str]) -> list[str]:
        # any 检查是否至少有一项为空白或超过 200 字。
        if any(not item.strip() or len(item) > 200 for item in values):
            raise ValueError("卖点不能为空或超过 200 字")
        return values