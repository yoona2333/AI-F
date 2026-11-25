"""接收两段文本，返回真实向量及本地计算的余弦，不生成聊天回答。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l3_2_embedding.schemas import EmbeddingCompareRequest
from lesson.l3_2_embedding import service

# 本节接口自动被脚手架发现。
router = APIRouter(prefix="/api/rag/embedding")

# POST 正文提供两段文本。
@router.post("/compare")
# 输入已校验对象，异步返回模型、维度、完整向量和分数。
async def compare(request: EmbeddingCompareRequest):
    # 两段一起请求，保证模型、维度和返回顺序一致。
    vectors = await service.embed([request.firstText, request.secondText])
    # 相似度由数值公式计算，不由模型编造。
    score = service.cosine(vectors[0], vectors[1])
    # 与页面约定使用驼峰键，向量是数组，不是 JSON 字符串。
    return Result.success({"model": service.model_name(), "dimension": len(vectors[0]), "firstVector": vectors[0], "secondVector": vectors[1], "score": score})