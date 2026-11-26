from io import BytesIO
from pathlib import Path
from uuid import uuid4
import pymupdf
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
from tortoise.expressions import RawSQL
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.l3_3_documents.models import RagDocument
from settings import settings

# 无输入参数，返回摘要，不将全文或服务器路径发送到列表页面。
async def list_documents():
    # all() 查询文档；annotate 添加临时查询字段 characters，CHAR_LENGTH(content) 在 MySQL 中计算字符数。
    # order_by("-id") 按编号倒序排列，新上传的排在前面；values 只取摘要字段，不加载全文和磁盘路径。
    # RawSQL 这里是固定表达式，不拼接用户输入；await 等数据库查询完成后才取得 rows 列表。
    rows = await RagDocument.all().annotate(characters=RawSQL("CHAR_LENGTH(content)")).order_by("-id").values("id", "original_name", "file_type", "characters", "chunked", "vectorized")
    # rows 中每项都是字典；逐项把数据库下划线字段转换为前端的 originalName、fileType。
    # characters 是刚才查询计算出的别名，不是需要增加到数据表里的真实列。
    return [{"id": row["id"], "originalName": row["original_name"], "fileType": row["file_type"], "characters": row["characters"], "chunked": row["chunked"], "vectorized": row["vectorized"]} for row in rows]

# 输入编号，返回前端详情；有意不返回 storage_path。
async def get_document(document_id):
    # filter(id=document_id) 按主键筛选，值由 ORM 绑定；first() 返回第一条对象，没有记录时返回 None。
    # await 等查询结束，row 是文档对象，后面可以通过 row.content 读取字段。
    row = await RagDocument.filter(id=document_id).first()
    # 防止后续代码对不存在的原文继续处理。
    if row is None:
        # 公共处理将异常转换为 Result。
        raise CustomException(ResultCodeEnum.NOT_FOUND, "文档不存在")
    # 把对象字段整理成普通字典，FastAPI 再把它序列化为 JSON。
    # content 是保存的解析原文；storage_path 仅供服务器内部使用，不放进响应。
    return {"id": row.id, "originalName": row.original_name, "fileType": row.file_type, "content": row.content, "chunked": row.chunked, "vectorized": row.vectorized}

# 输入原始字节与已校验格式，返回文本；损坏、加密和解码错误由上传业务处理。
def parse(data, file_type):
    # data 是上传文件的 bytes（二进制字节），file_type 是已经校验过的扩展名。
    # PDF 分支只提取已有文字层；图片中的字不会因为调用 get_text 就自动变成文本。
    if file_type == "pdf":
        # stream=data 表示直接从内存字节打开；filetype="pdf" 告诉 PyMuPDF 按 PDF 解析。
        # with 是资源管理语法，离开代码块时自动关闭文档，即使中途抛异常也会释放资源。
        with pymupdf.open(stream=data, filetype="pdf") as document:
            # 加密文件不能在未授权解密时当作正常资料。
            if document.needs_pass:
                # 外层转换为明确的解析失败提示。
                raise ValueError("PDF需要密码")
            # 遍历 document 得到每一页，page.get_text() 返回该页已有文字层中的字符串。
            # "\n".join(...) 用换行连接各页文字；阅读顺序由解析器给出，不等于完整还原原排版。
            return "\n".join(page.get_text() for page in document)
    # Word 只支持 Office Open XML 的 docx。
    if file_type == "docx":
        # BytesIO 把 bytes 包装成可读取的内存文件；python-docx 的 Document 据此打开 DOCX。
        # DOCX 内部是打包的 XML 文档，不能像 TXT 一样直接 decode 成正文。
        document = Document(BytesIO(data))
        # blocks 是按正文顺序累积的字符串列表，最后再合并成一段文本。
        blocks = []
        # iter_inner_content() 依次返回正文中的段落 Paragraph 或表格 Table。
        # 按这个顺序遍历，可以保留“段落 → 表格 → 段落”的先后关系。
        for block in document.iter_inner_content():
            # isinstance 判断当前对象类型；Paragraph.text 取得整段文字，标题也是段落。
            if isinstance(block, Paragraph):
                # 不把标题文本漏掉。
                blocks.append(block.text)
            # 遇到 Table 时继续遍历各行；每行拼成一条字符串，而不是把整张表丢掉。
            elif isinstance(block, Table):
                # 每一行独立进入解析文本。
                for row in block.rows:
                    # row.cells 是该行单元格；cell.text 取单元格正文，用 "\t" 制表符隔开各列。
                    # 这里保留表格文字，不生成 HTML 表格，也不包含原文档的样式。
                    blocks.append("\t".join(cell.text for cell in row.cells))
        # 最终统一为有换行的纯文本。
        return "\n".join(blocks)
    # PDF、DOCX 分支已经 return，剩下的已允许类型只有 md、txt。
    # decode 将 bytes 转成 str；utf-8-sig 兼容普通 UTF-8，并去掉文件开头可能存在的 BOM。
    # 非 UTF-8 数据会抛 UnicodeDecodeError，交给 upload 转成统一解析失败提示。
    return data.decode("utf-8-sig")

# 输入 FastAPI UploadFile，返回保存后的详情；失败不生成成功文档记录。
async def upload(file):
    # file 是 FastAPI 的 UploadFile，read 是异步读取方法，返回 bytes。
    # 5*1024*1024 是 5MB；多读 1 字节是为了判断文件是否已经超出上限。
    data = await file.read(5 * 1024 * 1024 + 1)
    # 字节已经在 data 中，关闭 UploadFile 的临时文件资源不影响后续解析 data。
    await file.close()
    # 空文件或超过 5 MB 都拒绝。
    if not data or len(data) > 5 * 1024 * 1024:
        # 提示与文件实际限制一致。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "请选择不超过5MB的非空文件")
    # filename 来自上传请求，可能为空，也可能夹带路径；这里只提取最后的显示名称。
    # 先把 Windows 反斜杠换成 /，再 rsplit("/", 1) 从右边切一次，[-1] 取最后一段。
    name = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    # 不让数据库字段被超长或空文件名占用。
    if not name.strip() or len(name) > 255:
        # 用户文件名不参与后面磁盘路径拼接。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "文件名不合法")
    # rsplit(".", 1) 按最后一个点分开，[-1] 取扩展名；lower() 让 PDF 和 pdf 使用同一分支。
    file_type = name.rsplit(".", 1)[-1].lower()
    # 旧 doc 在本节要求先另存为 docx。
    if file_type not in {"pdf", "docx", "md", "txt"}:
        # 格式判断不代替真正解析。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "仅支持PDF、DOCX、Markdown和TXT")
    # 先解析，成功后才写原件与数据库。
    try:
        # parse 先返回 str；依次把 Windows 换行和单独回车统一成 \n。
        # 去掉空字符 \x00，再 strip() 清除首尾空白；正文中的正常空格和换行仍保留。
        content = parse(data, file_type).replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").strip()
    # 损坏文件、密码和文本解码异常都作为解析失败处理。
    except Exception:
        # 不把乱码或空资料伪装成知识库文档。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "解析失败，请检查文件格式、编码或加密状态")
    # Python len 按 Unicode 码点计数，本章不把字符数当成 Token 数。
    if not content or len(content) > 50000:
        # 无文字层的扫描 PDF 会被拒绝。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "未解析到文字或文本超过50000字符")
    # Path 把配置字符串转成路径对象；resolve() 转成绝对路径，/ "rag" 拼接子目录。
    directory = Path(settings.file_storage_path).resolve() / "rag"
    # parents=True 在父目录不存在时一并创建；exist_ok=True 表示目录已存在也不报错。
    directory.mkdir(parents=True, exist_ok=True)
    # uuid4() 生成随机编号，str() 转成文件名字符串，再拼接已校验的扩展名。
    # 两个用户上传同名文件时也有不同存储名，原始名称只保存在 original_name 中。
    target = directory / (str(uuid4()) + "." + file_type)
    # write_bytes 将原始二进制写入目标路径，保存的是原件，不是刚才解析出的纯文本。
    target.write_bytes(data)
    # 保存失败需要清理本次新创建的原件。
    try:
        # create 写入数据库并返回带主键的 ORM 对象；storage_path 存磁盘路径，content 存解析文本。
        # chunked、vectorized 未传入时使用默认值 0，row.id 是数据库生成的文档编号。
        row = await RagDocument.create(original_name=name, file_type=file_type, storage_path=str(target), content=content)
    # 只处理本次保存失败，不删除整个目录。
    except Exception:
        # 只删除本次刚写入的 target；missing_ok=True 表示文件已不存在时不再报错。
        # 这一步补偿文件写入，不代表数据库与文件系统处于同一个事务。
        target.unlink(missing_ok=True)
        # 单独的 raise 会把当前异常原样继续抛出，由公共异常处理记录并返回失败。
        raise
    # 通过新增编号读取完整详情，不猜测数据库主键。
    return await get_document(row.id)