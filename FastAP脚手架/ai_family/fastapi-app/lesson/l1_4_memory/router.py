from fastapi import APIRouter
from common.result import Result
from lesson.l1_4_memory.schemas import ChatRequest
from lesson.l1_4_memory import service

router = APIRouter(prefix="/api/memory")


@router.get("/messages")

async def messages():
    # 等待数据库读取完成，消息列表放入 data 字段。
    return Result.success(await service.list_messages())

# POST 请求提交当前问题，不接收前端拼装的历史。
@router.post("/chat")
# 接收校验后的请求，返回回答及历史条数。
async def chat(request: ChatRequest):
    # 将问题交给业务函数，成功结果使用统一格式返回。
    return Result.success(await service.chat(request.question))