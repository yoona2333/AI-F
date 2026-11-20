from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from common.result import Result
from lesson.l1_7_assistant.schemas import AssistantRequest
from lesson.l1_7_assistant import service

router = APIRouter(prefix="/api/assistant")


@router.get("/messages")
async def messages():
    return Result.success(await service.list_messages())

# POST 接收当前问题，返回流式响应。
@router.post("/stream")
async def stream(request: AssistantRequest):
    return StreamingResponse(service.stream_chat(request), media_type="text/event-stream")