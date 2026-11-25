"""恢复历史并执行工具查询，成功后保存本轮完整问答。"""
from langchain_core.messages import AIMessage, HumanMessage
from lesson.l1_4_memory.models import MemoryMessage
from lesson.l2_4_shop_assistant.tool_runner import run_query

# 无输入参数，按顺序返回全部已保存问答，供页面恢复。
async def list_messages():
    # 页面只读取编号、发言者和正文。
    return await MemoryMessage.all().order_by("id").values("id", "role", "content")

# 输入当前问题，返回本轮回答与工具记录；生成成功后依次保存问答。
async def chat(question):
    # 最新 20 条历史用于理解连续追问，不删除更早数据。
    rows = await MemoryMessage.all().order_by("-id").limit(20)
    # 恢复较早发言在前的顺序。
    rows.reverse()
    # 每个请求创建独立消息列表，不使用全局共享历史。
    messages = []
    # 把数据库发言者映射成框架消息。
    for row in rows:
        # 保留用户和助手的身份，不把历史拼成一大段文字。
        message = HumanMessage(content=row.content) if row.role == "user" else AIMessage(content=row.content)
        # 按发言顺序加入历史。
        messages.append(message)
    # 本轮问题只追加一次，位于历史之后。
    # 本轮重新查询的要求只进入模型上下文，数据库仍保存用户原始问题。
    current_question = question + "\n请执行本轮所需工具再回答；历史只用于理解指代，缺少查询条件时先询问。"
    # 当前问题只追加一次，带上本轮查询要求。
    messages.append(HumanMessage(content=current_question))
    # 框架在本次状态中自动追加工具请求和工具结果。
    response = await run_query(messages)
    # 有完整有效回答后先保存用户问题。
    await MemoryMessage.create(role="user", content=question)
    # 再保存最终回答，不保存临时工具消息。
    await MemoryMessage.create(role="assistant", content=response["answer"])
    # 返回本轮实际工具记录和最终正文。
    return response