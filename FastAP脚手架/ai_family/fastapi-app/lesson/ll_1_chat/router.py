
from fastapi import APIRouter

from common.result import Result
from lesson.ll_1_chat.schemas import SyncChatRequest
from lesson.ll_1_chat.service import chat

router = APIRouter(prefix="/api/chat")


@router.post("/sync")

def sync_chat(request: SyncChatRequest) -> Result:

    return Result.success(chat(request))