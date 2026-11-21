from fastapi import APIRouter
from common.result import Result
from lesson.l2_3_shop_tools.schemas import ShopChatRequest
from lesson.l2_3_shop_tools import service


router = APIRouter(prefix="/api/shop-tools")


@router.post("/chat")

async def chat(request: ShopChatRequest):
    return Result.success(await service.chat(request.question))