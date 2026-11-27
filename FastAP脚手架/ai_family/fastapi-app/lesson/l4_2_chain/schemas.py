"""当前商品资料请求，由各节路由校验；不从页面接收已经生成的节点结果。"""
from pydantic import BaseModel, Field, field_validator

# FastAPI 把 JSON 正文绑定为 CopyRequest 并先校验 product；通过后路由才用 request.product 建立初始 State。
# points、copy、title 是图运行时生成的产物，不属于这里声明的用户输入字段。
class CopyRequest(BaseModel):
    # str 声明字符串类型，没有默认值表示必填；min_length=1 拒绝空串，max_length=3000 限制资料规模。
    # 全空格也有长度，所以另用 not_blank 检查；这里计字符，不是模型 Token 数。
    product: str = Field(min_length=1, max_length=3000)

    # 为 product 添加字段校验，在 Pydantic 完成类型与长度检查后执行。
    @field_validator("product")
    # 类方法接收当前模型类及字段值，不依赖某个请求实例的可变属性。
    @classmethod
    # cls 是当前模型类，value 是已完成类型和长度检查的 product 字符串，本函数不读取类属性。
    # 返回 value 表示通过并保存为请求字段；抛 ValueError 表示参数无效，由公共处理转换为错误响应，不进入模型请求。
    def not_blank(cls, value: str) -> str:
        # strip 仅用于判断；空白资料不能作为有效商品进入模型节点。
        if not value.strip():
            # 抛 ValueError 让 Pydantic 汇总为参数错误，由公共处理统一响应。
            raise ValueError("商品资料不能为空")
        # 返回原文而不是 strip 后的副本，保留用户实际资料。
        return value