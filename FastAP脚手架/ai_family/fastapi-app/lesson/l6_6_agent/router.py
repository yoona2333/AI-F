"""提供已保存历史与本次客服问答事件流。"""
from fastapi import APIRouter
from common.result import Result
from lesson.l5_2_react.schemas import ReactRequest
from lesson.l6_6_agent import service

# 前缀对应本课节页面的历史读取与POST流式请求。
router = APIRouter(prefix="/api/mcp/agent")

# 注册GET /api/mcp/agent/messages，无正文参数，只读取已保存问答，不调用模型或查询工具。
@router.get("/messages")
# 历史入口：无输入参数，await等待读取，返回Result.data中的id/role/content数组，按id升序供页面恢复。
# 数据库异常交公共异常处理；只有普通JSON历史使用Result包装，不是SSE事件。
async def messages():
    # 只有普通JSON历史用Result包装，页面据此恢复已有内容。
    return Result.success(await service.list_messages())

# 注册POST /api/mcp/agent/stream，JSON正文先转ReactRequest并校验question非空白与最多2000字符。
@router.post("/stream")
# 流式入口：输入已校验request，读取request.question交服务，返回EventSourceResponse供框架消费。
# 不等待整图完成、不用Result包事件流；建立流后的tool/delta/done/error由服务的内部生成器逐步yield。
async def stream(request: ReactRequest):
    # 事件流不包Result，实际问答在消费响应时执行。
    return service.stream(request.question)