"""读取和重新生成文档片段，路径与页面提交保持一致。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l3_4_chunks.schemas import RagChunkRequest
from lesson.l3_4_chunks import service

# 片段列表和生成使用相同前缀，HTTP 方法区分操作。
router = APIRouter(prefix="/api/rag/chunks")

# GET 查询参数叫 documentId，保持页面小驼峰字段。
@router.get("")
# 输入文档编号，返回按片段序号排序的列表。
async def chunks(documentId: int):
    # await 等查询完成；Result.success 把列表包装为 code、data 等统一响应字段，不触发切分。
    return Result.success(await service.list_chunks(documentId))

# POST 正文提供文档编号和窗口参数。
@router.post("")
# 输入已校验对象，返回完整保存的片段列表。
async def create(request: RagChunkRequest):
    # FastAPI 已按 RagChunkRequest 校验基本范围；业务还会检查 overlap 小于 chunkSize。
    # await 等数据库替换完成再返回成功，不把刚开始处理当成保存成功。
    return Result.success(await service.create_chunks(request))