"""按两条一批生成片段向量，全部保存成功才标记文档完成。"""
import json
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.l3_2_embedding import service as embedding
# 复用 3-4 定义的文档查询，返回可更新向量化状态的 ORM 对象。
from lesson.l3_4_chunks.service import require_document
from lesson.l3_4_chunks.models import RagChunk
from lesson.l3_4_chunks.service import list_chunks

# 输入 document_id 文档主键，读取已切分片段，分批生成并保存向量，返回更新后的片段字典列表。
# 列表包含片段编号、原文、模型名及维度，不包含完整向量；未切分、空片段或请求失败会抛异常。
# 整篇完成状态最后才设置；失败不撤销已经写入的批次，但该文档会保持未完成而被检索排除。
async def vectorize(document_id):
    # 必须是已经存在且切分完成的文档。
    # document_id 来自请求中的文档编号；返回的是 RagDocument 对象，可以读取状态并调用 save，不是页面详情字典。
    document = await require_document(document_id)
    # 原文存在不代表片段已经保存成功。
    # chunked=1 才表示上次切分全部保存成功；其他状态直接抛异常，后面的向量请求和数据库写入都不会发生。
    if document.chunked != 1:
        # 不把未切分的整篇文字直接当成一个已有片段。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "请先完成文档切分")
    # 按原文序号读取，批量返回数组与输入顺序对应。
    # filter 限定当前文档，order_by 按片段阅读顺序升序；没有 values，因此 rows 中每项是可以 save 的 ORM 对象。
    rows = await RagChunk.filter(document_id=document_id).order_by("chunk_index")
    # 空片段集不能被标记为成功向量化。
    # 空列表在布尔判断中为 False；没有片段就停止，不把“没有任何向量需要保存”误判成处理完成。
    if not rows:
        # 提示先核对切分和学习库。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "文档没有片段")
    # 重做时先标记未完成，检索不使用部分旧向量或半成品结果。
    # 这里只改内存对象，还未更新 MySQL；先清除完成标记，防止后续批次失败时仍被检索当作完整资料。
    document.vectorized = 0
    # 保存整篇状态，不修改原文。
    # save 将当前 vectorized 值写入数据库；update_fields 只更新这一列，不覆盖原文和切分状态。
    await document.save(update_fields=["vectorized"])
    # range 的步长为 2，即每批最多两条，末批可能一条。
    # range 的起点为 0，终点不包含 len(rows)，每次加 2；例如 5 条片段，三批起点依次是 0、2、4。
    for start in range(0, len(rows), 2):
        # 切片不会越界，保留当前批次的原始顺序。
        # 切片包含左端、不包含右端；5 条时依次取得下标 [0,1]、[2,3]、[4]，末批不足两条也不会越界。
        batch = rows[start:start + 2]
        # 每条片段独立向量化，不把一批文本拼成一个输入。
        # 列表推导式逐条取正文，得到 [第一片正文, 第二片正文]；保持顺序，不拼成一个字符串，否则无法获得一片一向量。
        texts = [row.content for row in batch]
        # 真正请求模型，统一业务会检查返回条数与维度。
        # 复用 3-2：await 等真实 Embedding 请求完成，返回二维数值列表；vectors[0] 对应 texts[0]，该服务已检查条数和 256 维。
        vectors = await embedding.embed(texts)
        # 相同下标的向量对应当前批次相同位置的片段。
        # enumerate 同时提供从 0 开始的位置 index 和片段对象 row；这个位置用于取当前批次中一一对应的向量，不是片段主键。
        #Python 的 `enumerate` 循环，**同时拿到下标和元素**
        for index, row in enumerate(batch):
            # dumps 将数值数组编码成 JSON 字符串，数据库字段保存该字符串。
            # vectors[index] 原来是浮点数列表，dumps 将其变成如 "[0.12, -0.03]" 的 JSON 文本，适配表中的文本字段。
            row.embedding_json = json.dumps(vectors[index])
            # 保存模型名，不能只靠维度判断是否同一个向量空间。
            # 把本次生成所用的模型名一起保存；即便两个模型输出维度相同，得到的向量也不能直接混用比较。
            row.embedding_model = embedding.model_name()
            # 保存实际维度，不伪造一个固定显示值。
            # len 取得这条实际向量的分量个数；不是正文字符数，也不是模型消耗的 Token 数。
            row.dimension = len(vectors[index])
            # 按当前对象主键更新，不能用 chunk_index 代替主键。
            # 按 row 自带的数据库主键更新这条片段，只写向量、模型和维度；await 等本条落库后再处理下一条。
            await row.save(update_fields=["embedding_json", "embedding_model", "dimension"])
    # 所有批次与写入均成功才标记完成；失败可以重新对整篇执行。
    # 只有所有批次和每条保存均未抛异常才到这里；后面的 save 把整篇标成完成，中途失败则保留未完成状态。
    document.vectorized = 1
    # 这是普通顺序操作，不保证中途失败时全部回滚。
    # save 将当前 vectorized 值写入数据库；update_fields 只更新这一列，不覆盖原文和切分状态。
    await document.save(update_fields=["vectorized"])
    # 返回数据库实际保存的信息，刷新后仍可查看。
    # 重新查询数据库，返回片段字典列表（含编号、正文、模型名、维度），不是把完整向量数组发送到页面。
    return await list_chunks(document_id)