import math
from langchain_openai import OpenAIEmbeddings
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from settings import settings

# 无输入参数，返回后端配置的实际 Embedding 模型名。
def model_name():
    # 模型名与向量一起保存，用于检索时核对来源空间。
    return settings.bailian_embedding_model

# 输入最多十条非空文本，异步返回按输入顺序排列的 256 维数组。
async def embed(texts):
    # 空凭证不发送模型请求。
    if not settings.bailian_api_key.strip():
        # 由脚手架异常处理转换为统一响应。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "请先配置百炼 API Key")
    # 模型单次最多十条，本章实际每批最多两条。
    if not texts or len(texts) > 10 or any(not text.strip() for text in texts):
        # 空文本不能直接进入向量化。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "向量化文本不能为空，每批最多十条")
    # Embedding 客户端与聊天客户端不同，不用聊天模型猜一个向量。
    model = OpenAIEmbeddings(
        model=model_name(),
        api_key=settings.bailian_api_key,
        base_url=settings.bailian_base_url,
        dimensions=256,
        chunk_size=10,
        check_embedding_ctx_length=False,
        request_timeout=45,
        max_retries=0,
    )
    # 一次批量请求，await 等完整数组，不表示流式输出。
    vectors = await model.aembed_documents(texts)
    # 返回顺序对应输入顺序，必须核对条数和维度再保存。
    #防止：部分文本向量化失败、模型丢返回、接口截断，导致向量和文本错位（A 文本的向量贴给 B 文本，检索灾难）
    #约束：你这个 Embedding 模型固定输出**256 维向量**，任意一条向量维度不对就直接抛错，不进向量库
    # 条件1：向量总数和文本数量对不上 → 报错
    # 条件2：任意一个向量维度不是256 → 报错
    #**保证后续能正常计算余弦相似度；同时也是为了满足向量数据库的存储约束**
    if len(vectors) != len(texts) or any(len(vector) != 256 for vector in vectors):
        # 不把缺失或异常向量错误对应到其他片段。
        raise ValueError("向量条数或维度与输入不一致")
    # 每个内层数组是一段文本的向量。
    return vectors

# 输入两个等长非零数组，返回余弦；分数在 [-1,1] 内，不是正确率。
def cosine(first, second):
    # 维度不同就没有逐项对应关系。
    if not first or len(first) != len(second):
        # 不截断或补零来掩盖模型不一致。
        raise ValueError("向量维度不一致")
    # 累积点积和两条向量长度的平方。
    dot = first_norm = second_norm = 0.0
    # 相同下标表示同一维，逐项相乘求和。
    for i in range(len(first)):
        # 拒绝 NaN 和无穷，避免生成不能排序的分数。
        if not math.isfinite(first[i]) or not math.isfinite(second[i]):
            # 无效数组不能用于真实检索。
            raise ValueError("向量含无效数值")
        # 点积是对应分量乘积之和。
        dot += first[i] * second[i]
        # 长度计算要先对各项平方再求和。
        first_norm += first[i] * first[i]
        # 第二个向量独立累积长度。
        second_norm += second[i] * second[i]
    # 零向量没有方向，不能作为分母。
    if first_norm == 0 or second_norm == 0:
        # 不把这种情况伪装成相似度为零。
        raise ValueError("不能计算零向量的余弦")
    # 点积除以两个长度之积，限制轻微浮点越界。
    #**钳位（clamp），强制结果范围 [-1.0, 1.0]**
    return max(-1.0, min(1.0, dot / (math.sqrt(first_norm) * math.sqrt(second_norm))))