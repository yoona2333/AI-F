"""接收本节问题，等待手写循环结束后返回回答、完成状态和实际工具记录。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l5_2_react.schemas import ReactRequest
from lesson.l5_2_react import service

# 本节接口前缀独立，完整地址由前缀和下面/run拼成，不影响现有工具查询页面。
router = APIRouter(prefix="/api/agent/react")

# 注册POST /api/agent/react/run，页面用JSON提交question；注册阶段不会执行模型或工具。
@router.post("/run")
# request由FastAPI按ReactRequest校验，输出Result.data含answer/completed/steps；执行异常交公共处理，不报告成功。
async def run(request: ReactRequest):
    # 只取本次question传给服务，await等全部决策轮结束；业务成功响应也要看completed才能区分正常完成与上限退出。
    return Result.success(await service.run(request.question))