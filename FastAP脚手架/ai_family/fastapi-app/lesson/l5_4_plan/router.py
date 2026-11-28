"""接收商品对比问题，返回计划、真实查询记录及最终建议。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l5_2_react.schemas import ReactRequest
from lesson.l5_4_plan import service

# 当前请求仍只有question，直接使用已有问题校验对象。
router = APIRouter(prefix="/api/agent/plan")

# 注册POST /api/agent/plan/run，正文在进入函数前完成校验。
@router.post("/run")
# 输入已校验问题，等待完整规划执行后返回Result；失败由公共异常处理提示。
async def run(request: ReactRequest):
    # service返回的是整次结果，不是规划模型的第一次响应。
    return Result.success(await service.run(request.question))