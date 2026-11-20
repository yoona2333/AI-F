from fastapi import APIRouter
from common.result import Result
from lesson.l1_6_usage.schemas import UsageRequest
from lesson.l1_6_usage.service import chat


router = APIRouter(prefix="/api/usage")

@router.post("/chat")
async def call(request: UsageRequest):
    return Result.success(await chat(request))