"""上传与原文详情接口；脚手架自动注册，不修改公共文件上传。"""
from fastapi import APIRouter, File, UploadFile
from common.result import Result
from lesson.l3_3_documents import service

# 与文档列表、详情统一前缀。
router = APIRouter(prefix="/api/rag/documents")

# 无输入正文的普通 GET。
@router.get("")
# 返回全部已解析文档摘要，供列表和下拉框使用。
async def documents():
    # 数据库读取结果包装成统一响应。
    return Result.success(await service.list_documents())

# 路径编号对应数据库文档主键。
@router.get("/{document_id}")
# 输入整数编号，返回包含纯文本的详情，不含磁盘路径。
async def detail(document_id: int):
    # 不存在时业务抛出明确错误。
    return Result.success(await service.get_document(document_id))

# POST multipart 的字段名为 file。
@router.post("/upload")
# 输入框架读取的上传文件，返回保存后的真实文档记录。
async def upload(file: UploadFile = File()):
    # 普通查询函数之外，上传业务负责校验格式、大小和解析内容。
    return Result.success(await service.upload(file))