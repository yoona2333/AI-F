"""读取历史、调用模型、保存问题与回答。"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.l1_4_memory.models import MemoryMessage


async def list_messages():
    return await MemoryMessage.all().order_by("id").values("id", "role", "content")

# 接收当前问题，读取最近历史，生成并保存回答，返回回答及历史条数。
async def chat(question):
    # 倒序取最新 20 条；数据库仍保留更早的消息。
    rows = await MemoryMessage.all().order_by("-id").limit(20)
    # 将倒序结果反转，恢复较早消息在前的发言顺序。
    rows.reverse()
    messages = [SystemMessage(content="你是一位数码商城助手，请根据对话历史回答用户。")]
    for row in rows:
        message = HumanMessage(content=row.content) if row.role == "user" else AIMessage(content=row.content)
        messages.append(message)

    messages.append(HumanMessage(content=question))

    reply = await get_chat_model().ainvoke(messages,
        extra_body={"enable_thinking": False, "max_tokens": 1024})
    # 空白或非文字结果不能作为有效历史保存。
    if not isinstance(reply.content, str) or not reply.content.strip():
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "模型没有返回有效回答，请重试")

    await MemoryMessage.create(role="user", content=question)
    await MemoryMessage.create(role="assistant", content=reply.content)
    return {"answer": reply.content, "historyMessages": len(rows)}