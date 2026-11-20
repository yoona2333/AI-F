from typing import Literal
from pydantic import BaseModel, Field, field_validator


class HistoryItem(BaseModel):

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class UsageRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[HistoryItem] = Field(default_factory=list, max_length=40)
    contextBudget: int = Field(default=2000, ge=300, le=12000, strict=True)
    @field_validator("question")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("问题不能为空")
        return value


    @field_validator("history")
    @classmethod
    def complete_turns(cls, values: list[HistoryItem]) -> list[HistoryItem]:
        # 一轮有两条，奇数条说明有半轮记录。
        if len(values) % 2:
            # 拒绝无法按整轮裁剪的历史。
            raise ValueError("历史必须按 user、assistant 顺序成对填写")
        # enumerate 同时提供消息位置和内容。
        for index, item in enumerate(values):
            # 偶数位置是提问，奇数位置是回答。
            expected = "user" if index % 2 == 0 else "assistant"
            # 身份顺序错误或正文空白都拒绝。
            if item.role != expected or not item.content.strip():
                # 返回便于页面理解的参数提示。
                raise ValueError("历史必须按 user、assistant 顺序成对填写，正文不能为空")
        # 空列表或有效完整问答均允许。
        return values