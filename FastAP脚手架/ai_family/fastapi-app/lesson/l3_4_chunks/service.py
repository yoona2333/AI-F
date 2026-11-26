"""按长度和重叠计算真实片段，再依次替换该文档的旧片段。"""
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.l3_3_documents.models import RagDocument
from lesson.l3_4_chunks.models import RagChunk

# 输入文档编号，返回数据库文档对象，供切分读取原文和更新处理状态。
async def require_document(document_id):
    # 复用 3-3 的表模型；filter 按主键查询，first 没有查到时返回 None。
    document = await RagDocument.filter(id=document_id).first()
    # 没有原文记录就停止处理，避免对不存在的文档创建片段。
    if document is None:
        # 交给公共异常处理返回“文档不存在”，此时还没有删除或写入片段。
        raise CustomException(ResultCodeEnum.NOT_FOUND, "文档不存在")
    # 返回 ORM 对象而不是页面详情字典，后面可以读取 content、修改状态并调用 save。
    return document

# 输入文档编号，返回数据库已保存片段的摘要和原文。
async def list_chunks(document_id):
    # filter 按所属文档筛选；order_by 按 chunk_index 升序恢复原文顺序。
    # values 指定只返回这些列，每行是字典，不是 ORM 对象，也不读取完整向量 embedding_json。
    # await 等数据库完成查询后，rows 才是可遍历的列表；没有片段时得到空列表。
    rows = await RagChunk.filter(document_id=document_id).order_by("chunk_index").values("id", "document_id", "chunk_index", "content", "dimension", "embedding_model")
    # 列表推导式遍历 rows，为每条 row 构造一个返回字典：document_id 改名为前端使用的 documentId。
    # embedding_model 为 None 或空串时用空字符串，供页面显示“未向量化”；这里不修改数据库记录。
    return [{"id": row["id"], "documentId": row["document_id"], "chunkIndex": row["chunk_index"], "content": row["content"], "dimension": row["dimension"], "embeddingModel": row["embedding_model"] or ""} for row in rows]

# 输入 text 原文、chunk_size 每片字符数、overlap 相邻片段重复字符数，返回按原文顺序排列的字符串列表。
# 此函数只计算，不修改数据库；参数错误或片段超过 1000 条时抛异常，调用方不会开始删除旧记录。
def                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             split(text, chunk_size, overlap):
    # 任一条件成立就拒绝：长度不在 100～1000、重叠不在 0～300、重叠不小于长度。
    # 例如长度 100、重叠 100 各自范围合法，但步长为 0，会一直停在同一位置，必须单独拦截。
    if not 100 <= chunk_size <= 1000 or not 0 <= overlap <= 300 or overlap >= chunk_size:
        # 错误在删除旧片段前抛出。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "重叠必须小于片段长度，参数超出允许范围")
    # 创建空列表，后面把每片原文追加到这里；Python 字符串切片按 Unicode 码点计数。
    # 一个组合表情可能由多个码点组成，按码点切分不保证整个组合表情都留在同一片。
    chunks = []
    # start 保存当前片的起始下标；字符串第一个字符下标为 0，对应读者看到的第 1 个字符。
    start = 0
    # len(text) 是原文码点数；只要当前起点小于全文长度就继续，空原文则直接返回空列表。
    while start < len(text):
        # 起点加窗口长度得到右边界，min 取较小值，使最后一片不超过全文末尾。
        # 例如全文 420 字、长度 150、重叠 30，起点为 0、120、240、360，末片右边界只能取 420。
        end = min(start + chunk_size, len(text))
        # text[start:end] 包含 start、不包含 end；text[0:150] 就是第 1～150 个字符。
        # append 把本片字符串加入列表；不 strip，避免边界空格或换行被删，影响精确重叠的核对。
        chunks.append(text[start:end])
        # 每追加一片就检查总数，防止重叠接近片长时产生大量几乎重复的片段。
        if len(chunks) > 1000:
            # 本次还没有对数据库执行删除或写入。
            raise CustomException(ResultCodeEnum.PARAM_ERROR, "片段过多，请减小重叠或增大片段长度")
        # 当前片已覆盖最后一个字符就停止，即使下一起点仍小于全文长度，也不再重复截取尾部。
        if end == len(text):
            # break 退出 while；接着执行循环后的 return，返回全部已算好的片段。
            break
        # 起点每次前进“片长减重叠”：150-30=120，第二片从下标 120（第 121 字）开始。
        # 第一片下标 120～149 的 30 字会再次出现在第二片开头；重叠为 0 时，两片直接相接。
        start += chunk_size - overlap
    # 返回内容按原文从前到后排序。
    return chunks

# 输入 RagChunkRequest，先查原文并计算片段，再替换数据库记录，返回保存后的字典列表。
# 原文从服务器读取，不使用页面传入的正文；顺序写入中途失败会抛异常，不会自动撤销之前的操作。
async def create_chunks(request):
    # request.documentId 是页面选中的文档主键；require_document 返回 ORM 对象，content 是已保存原文。
    document = await require_document(request.documentId)
    # 把原文和参数交给纯计算函数，返回 chunks 字符串列表；此时还未改变数据库。
    # 若 split 抛参数异常，下面清状态、删除旧片段等语句均不会执行，旧数据保留。
    chunks = split(document.content, request.chunkSize, request.overlap)
    # 先改内存对象：chunked=0 表示本次切分尚未全部保存；赋值本身还没有更新数据库。
    document.chunked = 0
    # 新边界可能改变片段内容，旧向量不能再用；vectorized=0 表示新片段需要重新向量化。
    document.vectorized = 0
    # save 才真正提交数据库更新；update_fields 只更新这两个状态列，不重复保存原文等字段。
    # 状态先落库为未完成，后面保存失败时也不会被当成已完成向量化的资料。
    await document.save(update_fields=["chunked", "vectorized"])
    # filter 限定只删当前文档；delete 删除整条旧片段记录，其旧向量也随记录一起移除。
    # rag_document 的原文仍在，其他文档的片段不受影响。
    await RagChunk.filter(document_id=document.id).delete()
    # enumerate 同时给出序号 index 和正文 content；start=1 让页面从“片段 1”开始。
    # chunk_index 是当前文档内顺序，不是数据库自增主键，不同文档都可以有片段 1。
    for index, content in enumerate(chunks, start=1):
        # 每轮 create 新增一条片段，保存所属文档、阅读序号和实际切出的文字，id 由数据库生成。
        # 未传的向量、模型名默认 NULL，dimension 默认 0，表示尚未向量化。
        await RagChunk.create(document_id=document.id, chunk_index=index, content=content)
    # 只有上面循环全部写入成功，才会把内存对象的 chunked 改成 1。
    document.chunked = 1
    # 把切分完成状态写回数据库，只更新 chunked；vectorized 仍为 0，下一步还要生成新向量。
    # 这里不是整体事务，失败可能留下部分片段，需要重新切分，不会自动回滚之前的删除和插入。
    await document.save(update_fields=["chunked"])
    # 重新查询数据库，返回带真实自增 id 的有序列表；页面展示实际保存结果，不自行编造主键。
    return await list_chunks(document.id)