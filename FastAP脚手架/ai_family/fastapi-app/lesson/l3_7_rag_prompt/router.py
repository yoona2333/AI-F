"""同步返回 RAG 回答、来源与实际用户 Prompt。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l3_6_search.schemas import RagSearchRequest
from lesson.l3_7_rag_prompt import service

# 回答与只检索接口分开。
router = APIRouter(prefix="/api/rag/answer")

# POST 正文仍沿用问题、TopK 与阈值。
@router.post("")
# 输入校验后的参数，返回完整回答或明确的无依据答复。
async def answer(request: RagSearchRequest):
    # 由后端执行本轮检索，不接收页面指定的片段正文。
    return Result.success(await service.answer(request))