"""向商城MCP服务器注册售后资料和客服模板；资源读取数据库原文，模板只生成消息。"""
from lesson.l3_3_documents.models import RagDocument
from lesson.l6_2_server.server import mcp

# 售后资源：无参数，读取名为01-售后政策.md的最新文档并返回原文；未上传时抛错，不编造政策。
# URI是协议资源标识，mime_type描述返回的纯文本格式；客户端用resources/read读取此入口。
@mcp.resource("mall://policies/after-sales", name="after_sales", mime_type="text/plain")
async def after_sales() -> str:
    # filter按原文件名精确查找，-id取最新上传；first返回一个ORM对象或None，不进行向量检索。
    document = await RagDocument.filter(original_name="01-售后政策.md").order_by("-id").first()
    # 没有对应原文就终止资源读取，错误由MCP返回给客户端。
    if document is None:
        # 明确提示缺少哪份资料，不能把其他文档当作售后政策。
        raise ValueError("请先上传并解析01-售后政策.md")
    # 返回来源文件名和数据库中真实解析原文；不修改文档、片段或向量。
    return "来源：" + document.original_name + "\n" + document.content

# 客服模板：orderNo是客户端提供的订单号，返回一条用户消息；获取模板不执行工具、不请求模型。
# @mcp.prompt注册名称customer_service和参数说明，客户端通过prompts/get传入字符串参数。
@mcp.prompt
def customer_service(orderNo: str) -> str:
    """根据订单号生成查询订单与物流的客服任务。"""
    # 去除首尾空白，1～40字符与订单查询一致，非法参数使模板获取失败。
    value = orderNo.strip()
    # or短路判断：空串或超过40字符均不生成任务。
    if not value or len(value) > 40:
        # 模板中不使用猜测的编号，要求客户端传入有效值。
        raise ValueError("订单号不能为空且最多40字符")
    # 字符串由FastMCP转换为用户消息；这是任务描述，还没有得到订单查询结果。
    return f"请查询订单 {value} 的状态和物流，根据实际工具结果回答；未查到时明确说明。"