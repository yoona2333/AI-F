import json
from langchain_core.messages import AIMessage, HumanMessage
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.l1_7_assistant.models import AssistantMessage


async def list_messages():
    # 按编号排序，仅返回页面需要的字段。
    return await AssistantMessage.all().order_by("id").values("id", "role", "content")

# 接收事件数据，返回标准 SSE 数据帧；两个换行表示一帧结束。
def event(data):
    # JSON 编码避免正文换行破坏帧边界，ensure_ascii=False 保留中文。
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"

# 接收校验后的请求，逐段产生 SSE；成功后保存完整问答并发送 done。
async def stream_chat(request):
    rows = await AssistantMessage.all().order_by("-id").limit(20)
    # 恢复较早消息在前的顺序。
    rows.reverse()
    # 按顺序组装历史消息，再追加当前问题。
    messages = []
    # 将历史记录恢复为模型消息。
    for row in rows:
        # user 对应 HumanMessage，assistant 对应 AIMessage。
        message = HumanMessage(content=row.content) if row.role == "user" else AIMessage(content=row.content)
        # 顺序追加每条历史发言。
        messages.append(message)
    # 当前问题放在历史之后。
    messages.append(HumanMessage(content=request.question))
    # 累积完整回答，结束时再写入 MySQL。
    answer = ""
    # 模型服务不返回用量时保持 None，不伪造统计数字。
    usage = None
    # 出错时给页面发送错误事件，让等待状态结束。
    try:
        model = get_chat_model().model_copy(update={"streaming": True})
        async for chunk in model.astream(messages, stream_usage=True,

            extra_body={"enable_thinking": False, "max_tokens": 1024}):

            if isinstance(chunk.content, str) and chunk.content:
                # 追加到完整回答，用于结束后保存。
                answer += chunk.content
                # 立即推送增量，让用户看到回答逐步出现。
                yield event({"type": "delta", "content": chunk.content})
            # 统计可能出现在最后一个没有正文的块中。
            if chunk.usage_metadata:
                # 保留服务提供的实际用量，不自行估算。
                usage = chunk.usage_metadata
        # 空回答没有保存价值，交给错误分支提示。
        if not answer.strip():
            # 抛出异常，使下方统一发送 error。
            raise ValueError("模型没有返回有效回答")
        # 完整生成后，将用户问题写入消息表。
        await AssistantMessage.create(role="user", content=request.question)
        # 再保存完整回答，不把增量逐段写入历史。
        await AssistantMessage.create(role="assistant", content=answer)
        # 通知页面完成并附带实际 Token 统计。
        yield event({"type": "done", "usage": usage})
    # 生成或入库失败时结束本轮，页面保留已展示文字并提示失败。
    except Exception:
        # 向页面发送错误事件和提示文字。
        yield event({"type": "error", "message": "生成或保存失败，请检查后端日志和配置"})