"""提交本节工作流并等待完整State，错误由脚手架统一处理。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l4_2_chain.schemas import CopyRequest
from lesson.l4_2_chain import service

# 本节接口独立，完整地址为POST /api/workflow/2/run。
router = APIRouter(prefix="/api/workflow/2")

# 注册 POST /api/workflow/2/run，对应页面的 request.post；装饰器注册接口时不会启动文案图。
@router.post("/run")
# request: CopyRequest 使 FastAPI 先从 JSON 构造并校验商品请求，失败时不进入本函数。
# 返回 Result 的 data 是 product、points、copy、title；图异常交公共处理，不返回 code=200 的部分结果。
async def run(request: CopyRequest):
    # request.product 取出已校验原文交给服务；await 等整图完成，Result.success 把最终字典放入 data。
    # 页面读取 response.data.points、copy、title 展示三个阶段产物；本节没有渠道和评分字段。
    return Result.success(await service.run(request.product))