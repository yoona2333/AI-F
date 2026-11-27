"""校验本次问题；路由只接收question，模型决定的工具和结果由后端产生。"""
from pydantic import BaseModel, Field, field_validator

# FastAPI用此模型读取POST正文，校验完成后才把question传给手写循环。
class ReactRequest(BaseModel):
    # 必填字符串；最少1字符拒绝空串，最多2000字符限制输入规模，不等于模型Token数。
    question: str = Field(min_length=1, max_length=2000)

    # 在question通过类型与长度检查后执行额外的全空白检查。
    @field_validator("question")
    # 类方法由Pydantic调用，cls为当前请求类，不依赖某个请求实例的属性。
    @classmethod
    # value是当前问题；返回原字符串表示通过，空白时抛ValueError，由公共处理返回参数错误，不调用模型。
    def not_blank(cls, value: str) -> str:
        # strip只用于判断，不改变用户提交的原始文字和内部换行。
        if not value.strip():
            # 只有空格或换行也不能作为有效客服问题。
            raise ValueError("问题不能为空")
        # 保留原文供系统围绕用户的真实目标作判断。
        return value