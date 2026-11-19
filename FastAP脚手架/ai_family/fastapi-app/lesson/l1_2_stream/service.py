import json
import logging
from secrets import randbelow

from langchain_core.messages import HumanMessage
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.ll_1_chat.schemas import SyncChatRequest
from settings import settings

# 用当前模块名创建日志对象。
logger = logging.getLogger(__name__)


# 接收事件名和数据字典，返回 SSE 响应工具需要的事件字典。
def event(name: str, data: dict) -> dict:
    # event 是事件名称；data 编码为 JSON，ensure_ascii=False 保留中文字符。
    return {"event": name, "data": json.dumps(data, ensure_ascii=False)}


# 异步生成器：每次 yield 返回一条事件，由接口持续发送给页面。
async def stream_chat(request: SyncChatRequest):

    finish_reason = "UNKNOWN"
    # 记录本次实际使用的模型名；结束块没带时用配置里的名字兜底
    model_name = settings.bailian_chat_model
    # 记录本次 token 用量；只有开启 stream_usage 后才会在最后一块拿到
    usage = None

    try:
        # 复制模型配置并启用流式，复用底层连接，不修改同步对话的共享对象。
        # stream_usage=True 让服务端在流结束时补发一块用量信息。
        model = get_chat_model().model_copy(update={"streaming": True, "stream_usage": True})
        # 调用异步流接口；每次迭代取得一块结果，不等待完整答案。
        async for chunk in model.astream(
            [HumanMessage(content=request.question)],
            temperature=request.temperature,
            top_p=request.topP,
            seed=randbelow(2147483647) + 1,

            extra_body={"enable_thinking": False, "max_tokens": request.maxTokens},
        ):
            if chunk.content:
                # 把当前增量交给 SSE 响应，不拼成完整回答再返回。
                #`yield` 是 Python 生成器的关键字，作用：**暂停函数，返回一个值；下次进来，从暂停的地方继续往下跑**。
                yield event("message", {"content": chunk.content})
            # 即使正文为空，也读取该块可能携带的结束原因。
            reason = chunk.response_metadata.get("finish_reason")
            # 只有模型提供了结束原因，才更新记录。
            if reason:
                # 转成大写，供页面判断 STOP 或 LENGTH。
                finish_reason = str(reason).upper()
            # 结束块通常同时带模型名，取到就覆盖兜底值。
            name = chunk.response_metadata.get("model_name")
            if name:
                model_name = name
            # 用量只出现在最后补发的那一块，拿到就保存。
            if chunk.usage_metadata:
                usage = chunk.usage_metadata
        # 所有增量读取完后发送结束事件，附带模型名和 token 用量。
        # 这样浏览器开发者工具的 EventStream 里也能直接看到这些信息。
        yield event(
            "done",
            {
                "finishReason": finish_reason,
                "modelName": model_name,
                "usage": usage,
            },
        )
    # 推流开始后不能改成普通 JSON 响应，失败信息也通过 SSE 返回。
    except Exception:
        # 保存完整异常信息，不把内部异常细节直接展示给用户。
        logger.exception("流式模型调用失败")
        # 发送错误事件，不再发送 done。
        yield event("error", {"message": "生成失败，请检查后端日志"})