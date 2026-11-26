"""只返回来源与相似度，方便单独检查检索质量。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l3_6_search.schemas import RagSearchRequest
from lesson.l3_6_search import service

# 生成回答与检索分开，定位错误时不混在一起。
router = APIRouter(prefix="/api/rag/search")

# POST 请求携带完整检索问题与设置。
@router.post("")
# 输入已校验参数，输出真实命中片段与本轮计算的分数。
async def search(request: RagSearchRequest):
    # 返回空数组也是一种有效结果。
    return Result.success(await service.search(request))