"""从 MySQL 读取完成文档的向量，在内存计算和排序，不调用回答模型。"""
import json
from lesson.l3_2_embedding import service as embedding
from lesson.l3_3_documents.models import RagDocument
from lesson.l3_4_chunks.models import RagChunk

# 输入问题、TopK 与阈值对象，返回本轮实际命中的来源片段。
async def search(request):
    # 本次问题独立向量化，模型和维度与文档片段相同。
    # 模型接口接收文本列表，这里只放一个问题；先 await 得到二维列表，再用 [0] 取唯一的查询向量。
    query = (await embedding.embed([request.question]))[0]
    # 仅取整篇完成的文档，半成品批次即使有部分向量也不参与检索。
    # 只查整篇向量化成功的文档，并只取编号和名称；values 返回字典，半成品文档即使有部分向量也不会入选。
    documents = await RagDocument.filter(vectorized=1).values("id", "original_name")
    # 文档编号映射到文件名，用于给命中结果附加真实来源。
    # 字典推导式建立“文档主键 → 文件名”映射，例如 {7: "售后政策.md"}；后面用它为片段补充真实来源。
    names = {row["id"]: row["original_name"] for row in documents}
    # 没有有效文档时返回空结果，不临时编造证据。
    # 映射为空说明没有已完成的文档，直接返回 []；空结果表示没证据，不是临时造一条最相近的资料。
    if not names:
        # 后续回答层据此返回明确无依据答复。
        return []
    # 只读取已完成文档中有向量的片段，按主键稳定排列。
    # list(names) 取映射的所有键；__in 相当于 SQL IN，__isnull=False 要求向量非 NULL；按主键升序读取 ORM 对象。
    rows = await RagChunk.filter(document_id__in=list(names), embedding_json__isnull=False).order_by("id")
    # 收集达到阈值的片段。
    hits = []
    # 小规模教学数据采用全量内存计算，不是向量索引查询。
    for row in rows:
        # 同维度不代表同模型；两个条件都要匹配。
        # 任一条件不符就跳过：模型名不同，或保存的维度与当前问题向量长度不同；不能补零、截断或混合不同空间。
        if row.embedding_model != embedding.model_name() or row.dimension != len(query):
            # 旧模型或不同维度需要重新向量化，不截断或补零。
            continue
        # 数据库保存的是 JSON 文本，loads 还原为数值数组。
        # loads 与保存时的 dumps 相反：把数据库 JSON 字符串还原成浮点数列表，才能按相同下标计算点积。
        vector = json.loads(row.embedding_json)
        # 分数由点积与长度公式计算，不由聊天模型评分。
        # 输入问题向量和片段向量，调用 3-2 的本地公式；返回 [-1,1] 的相似度，不再调用聊天模型打分。
        score = embedding.cosine(query, vector)
        # 阈值过滤先执行，不能强行拿低分片段凑满 K 条。
        # 先过滤再取 TopK；例如阈值 0.3，0.25 被跳过，0.3 本身保留，不为了凑条数降低阈值。
        if score < request.threshold:
            # 当前片段不进入候选结果。
            continue
        # 只返回必要字段与原文，不把大段向量传回页面。
        # 每个命中项是一个字典，保留片段主键、所属文档、原文位置、真实文件名和本次分数；不返回大段向量。
        hits.append({"id": row.id, "documentId": row.document_id, "chunkIndex": row.chunk_index, "content": row.content, "originalName": names[row.document_id], "score": score})
    # 负分数使 sort 按得分降序；同分按主键升序，方便重复核对。
    # lambda 为每项生成排序键 (-分数, 主键)，Python 默认升序；分数取负实现高分在前，同分按主键升序。sort 原地修改 hits。
    hits.sort(key=lambda hit: (-hit["score"], hit["id"]))
    # 切片最多取 K 条，可能不足 K 或为空。
    # 从已排序列表开头最多截 K 条；例如三条里仅两条过阈值，topK=3 仍只返回两条，结果可以为空。
    return hits[:request.topK]