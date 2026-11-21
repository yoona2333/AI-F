from fastapi import APIRouter
from common.result import Result
from lesson.l2_2_manual_tool.schemas import ManualToolRequest
from lesson.l2_2_manual_tool import service

# 使用独立前缀，避免影响已有聊天接口。
router = APIRouter(prefix="/api/manual-tool")

# POST 提交本轮问题并等待完整回答。
@router.post("/chat")
# 接收已校验请求，返回包含模型回答和工具列表的统一响应。
async def chat(request: ManualToolRequest):
    # 历史与工具执行都不由页面提供，页面只传当前问题。
    return Result.success(await service.chat(request.question))