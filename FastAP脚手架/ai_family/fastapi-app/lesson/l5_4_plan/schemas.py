"""约束模型生成的商品查询计划，执行阶段只读取已校验的关键词。"""
from pydantic import BaseModel, Field, field_validator

# 一个步骤代表一次商品关键词查询，不含任意函数名或SQL命令。
class PlanStep(BaseModel):
    # keyword由规划模型给出，交已有商品查询函数使用，最大长度与商品工具一致。
    keyword: str = Field(min_length=1, max_length=100)

    # Pydantic在类型和长度检查后调用本方法，额外拒绝全空白关键词。
    @field_validator("keyword")
    # cls为PlanStep类，校验不依赖实例状态。
    @classmethod
    # 输入原关键词，返回原文表示有效；空白抛ValueError，整份计划停止执行。
    def not_blank(cls, value: str) -> str:
        # 只判断空白，不改变关键词内部的空格。
        if not value.strip():
            # 防止空条件被执行成没有明确目标的查询。
            raise ValueError("查询关键词不能为空")
        # 校验通过交给后续查询，数据库函数仍有自己的参数检查。
        return value

# 顶层计划包含1至3项，限制来自本例商品对比任务的规模。
class Plan(BaseModel):
    # 每项进一步转成PlanStep；空列表、超过3项或任一关键词无效均使JSON校验失败。
    steps: list[PlanStep] = Field(min_length=1, max_length=3)