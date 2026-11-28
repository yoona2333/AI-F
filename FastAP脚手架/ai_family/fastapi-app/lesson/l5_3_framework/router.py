"""接收当前完整问题，等待框架Agent后返回回答与工具记录。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l5_2_react.schemas import ReactRequest
from lesson.l5_3_framework import service

# 路由前缀与页面请求一致；请求模型仍是只有question的现有结构。
router = APIRouter(prefix="/api/agent/framework")

# 注册POST /api/agent/framework/run；FastAPI先把JSON正文转成ReactRequest，检查question长度与空白。
@router.post("/run")
# 请求入口：request为已校验对象，读取request.question交服务执行，返回Result.data中的answer/completed/steps。
# 页面只提交问题，工具名称、参数和结果由Agent产生；服务异常交脚手架公共处理，本函数不补默认结果。
async def run(request: ReactRequest):
    # await等待框架整次执行，Result只包装最终业务结果，不包装某一轮模型响应。
    return Result.success(await service.run(request.question))