"""接收当前问题与检索设置，返回带事件名的 SSE。"""
from fastapi import APIRouter
from lesson.l3_6_search.schemas import RagSearchRequest
from lesson.l3_8_rag_chat import service

# 当前问答路径为 /api/rag/chat/stream，由本节独立路由提供。
router = APIRouter(prefix="/api/rag/chat")

# POST 正文发送问题和检索设置，不能使用只能 GET 的 EventSource 客户端。
@router.post("/stream")
# 输入校验后的参数，返回 sources、delta、done 或 error 事件。
async def stream(request: RagSearchRequest):
    # 检索前置失败由普通异常处理返回 JSON，开始推流后由生成器发送 error。
    return await service.stream(request)