"""按文档执行批量向量化，复用文档编号校验对象。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l3_3_documents.schemas import RagDocumentRequest
from lesson.l3_5_vectors import service

# 独立处理接口，不改前面上传和切分的代码。
router = APIRouter(prefix="/api/rag/vectors")

# POST 正文只需要文档编号。
@router.post("")
# 输入 RagDocumentRequest（正文中只有正整数 documentId），返回 Result 包装的已保存片段列表。
# FastAPI 先做参数校验；await 等全部批次处理结束，不是边处理边向页面推送。
async def vectorize(request: RagDocumentRequest):
    # request.documentId 取已校验主键，service 返回字典列表；Result.success 再包装为 code、data 等字段。
    # 向量及完成标记均由后端实际处理产生，不能由前端提交一个“完成”状态代替模型调用。
    return Result.success(await service.vectorize(request.documentId))