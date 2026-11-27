"""提交本节工作流并等待完整State，错误由脚手架统一处理。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l4_3_route.schemas import ChannelRequest
from lesson.l4_3_route import service

# 本节接口独立，完整地址为POST /api/workflow/3/run。
router = APIRouter(prefix="/api/workflow/3")

# post注册当前路径，FastAPI会先将正文转为下面声明的请求对象。
@router.post("/run")
# request 为经过参数校验的请求对象，本节接口等待整图完成后返回 Result，data 含 product、channel、points、copy、title。
# 前端只提供用户输入，不提供生成结果；服务执行异常交公共处理，不返回残缺状态冒充成功。
async def run(request: ChannelRequest):
    # await 等当前课节的完整图，再将最终字典交 Result.success 包装到 data；这里不是单独执行一次聊天模型调用。
    return Result.success(await service.run(request))