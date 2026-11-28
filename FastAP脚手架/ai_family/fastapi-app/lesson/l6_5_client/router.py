"""提供工具目录和手动调用接口，页面只提交名称与参数，不直接访问MCP协议。"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from common.result import Result
from lesson.l6_5_client import service

# 请求对象承载一次工具调用；工具参数的具体结构由MCP服务器继续校验。
class CallRequest(BaseModel):
    # name为发现目录中的准确工具名，1～100字符限制空名和异常长输入。
    name: str = Field(min_length=1, max_length=100)
    # arguments必须是JSON对象，字段可能为keyword或orderNo，不能提交数组或JSON字符串。
    arguments: dict

# 前缀对应Vue调试页的普通业务请求，区别于协议入口/mcp。
router = APIRouter(prefix="/api/mcp/client")

# GET入口无参数，返回Result.data中的真实工具列表；连接失败交公共异常处理。
# 注册普通JSON工具目录接口，访问时才执行发现。
@router.get("/tools")
async def tools():
    # 等待MCP工具发现，Result只包装页面接口，不改变MCP协议格式。
    return Result.success(await service.list_tools())

# POST入口接收CallRequest，返回Result.data.result中的观察文本；校验和执行错误不返回成功对象。
# 请求正文先由Pydantic检查name和arguments，再进入函数。
@router.post("/call")
async def call(request: CallRequest):
    # 名称和参数按原字段传给客户端服务，await等待真实服务器返回。
    return Result.success(await service.call_tool(request.name, request.arguments))