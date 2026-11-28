"""将已注册工具的MCP服务器接入/mcp路由，并随FastAPI启动、关闭其HTTP会话管理器。本文件让这些工具能够通过 HTTP 被访问，并管理运行资源。"""
from contextlib import asynccontextmanager
from fastapi import APIRouter
from lesson.l6_2_server.server import mcp

# 拿到注册好的名为mall的mcp对象，通过http_app(path="/mcp") 把MCP服务器包装成一个能处理 HTTP 请求的 ASGI（Python Web 服务器和应用之间的一套接口规范） 应用
# 可以理解为：mcp_app能通过 HTTP 接收 MCP 请求，把处理结果通过 HTTP 返回。即：告诉内层 MCP 应用，在这个路径上处理 MCP 协议请求
mcp_app = mcp.http_app(path="/mcp")

# FastAPI生命周期入口：app是框架传入的主应用对象；本函数没有业务返回值，负责让MCP资源覆盖应用运行期间。
# @asynccontextmanager把含yield的异步生成器变成可供async with进入和退出的上下文管理器。
# FastAPI启动时进入它，执行到yield前的准备；服务关闭时从yield后恢复，完成退出清理，不是每次请求都重新进入。
@asynccontextmanager
async def lifespan(app):
    print("启动时执行")
    # mcp_app.lifespan是FastMCP提供的资源管理入口：进入时创建并运行Streamable HTTP会话管理器。
    # 会话管理器负责协议连接及其后台任务；只创建http_app或只登记URL，并不会自动替它完成这项启动准备。
    # async with：MCP 启动资源
    async with mcp_app.lifespan(app):
        # yield表示启动准备已完成，将控制权交回FastAPI，它此后才开始接收业务请求。
        # 这里没有yield某个查询结果；服务停止时生成器恢复执行，随即退出上方async with完成MCP清理。
        yield
    print("关闭时执行")

# router必须命名为router，脚手架discover_routers才会收集它，并在main.py中执行app.include_router(router)。
# lifespan=lifespan传入的是上面函数的引用，不是立即调用；include_router会把它合并进主应用已有生命周期。
# 因此数据库和MCP都能随主应用启动和关闭，下面只需新增课节路由文件即可接入。
router = APIRouter(lifespan=lifespan)

# 把该应用接入项目的 HTTP 路由，告诉外层 FastAPI：收到这个路径的 HTTP 请求，交给 mcp_app
# include_in_schema=False只是不将它列入普通OpenAPI接口文档；仍可通过MCP访问，也不会隐藏工具目录。
router.add_route("/mcp", mcp_app, methods=["GET", "POST", "DELETE"], include_in_schema=False)