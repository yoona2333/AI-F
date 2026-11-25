"""提供历史恢复与连续查询接口。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l2_4_shop_assistant.schemas import ShopChatRequest
from lesson.l2_4_shop_assistant import service

# 综合助手使用独立接口前缀。
router = APIRouter(prefix="/api/shop-assistant")

# 页面加载或刷新时读取历史。
@router.get("/messages")
# 无输入参数，返回统一包装的全部已保存消息。
async def messages():
    # 不从本接口恢复临时工具记录。
    return Result.success(await service.list_messages())

# POST 请求只提交当前问题。
@router.post("/chat")
# 输入经过校验的问题，返回已完成保存的本轮回答与执行记录。
async def chat(request: ShopChatRequest):
    # 复用问题校验对象，历史由业务读取。
    return Result.success(await service.chat(request.question))