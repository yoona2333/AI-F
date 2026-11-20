from time import perf_counter
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from openai import AuthenticationError
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from settings import settings


# 供 build_context 判断是否超限，不调用模型。
# messages 是 LangChain 消息列表；返回整数，即正文 UTF-8 字节数加固定余量。
# 这个数只用于演示裁剪，不是服务统计的真实 Token 数。
def estimate(messages):
    # 从 0 开始累计全部消息的粗估大小。
    total = 0
    # 逐条读取消息，不改变正文。
    for message in messages:
        # encode 将文字编码成 UTF-8 字节；len 计算字节数量，不是汉字数量。
        content_bytes = len(message.content.encode("utf-8"))
        # 加 16 模拟消息包装的余量，并非协议的精确开销。
        total += content_bytes + 16
    # 返回累计值，调用方将它与输入粗估阈值比较。
    return total


# 为 chat 准备本次实际要发送的消息，此函数不调用模型。
# system 是规则字符串，history 是按时间排列的完整问答消息列表。
# question 是当前问题字符串，budget 是输入粗估阈值。
# 依次返回：待发送消息列表、删除的历史条数、待发送消息的粗估大小。
# 规则加问题已经超限时抛出参数错误，因为删光历史也放不下。
def build_context(system, history, question, budget):
    # 这两条必须保留，历史将插在两者之间。
    base = [SystemMessage(content=system), HumanMessage(content=question)]
    # 基础消息已经超限时，删除历史也无法解决。
    if estimate(base) > budget:
        # 提示调整问题或预算，不调用模型。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "本轮问题加系统消息已超过教学预算，请缩短问题或调高预算")
    # 复制列表，裁剪不改变传入历史。
    retained = list(history)
    # 统计本次删除的消息数。
    removed = 0
    # 列表相加表示按顺序拼接：规则 + 保留历史 + 当前问题。
    messages = [base[0]] + retained + [base[1]]
    # 反复检查大小；只要仍超限，就继续删最早一轮。
    while estimate(messages) > budget:
        # [2:] 取下标 2 到末尾，丢弃前两条 user、assistant 消息。
        retained = retained[2:]
        # 一轮对应两条消息。
        removed += 2
        # 用裁剪后的历史重新组装，下一轮循环重新计算大小。
        messages = [base[0]] + retained + [base[1]]
    # 返回本次上下文及裁剪统计。
    return messages, removed, estimate(messages)


# 供 chat 从回复里取真实用量，不会为了统计再调用一次模型。
# message 是 ainvoke 返回的 AIMessage，含回答正文和服务附带的数据。
# 返回前端需要的三个统计字段；缺失用量时返回 None（JSON 中是 null）。
def usage_from(message):
    # LangChain 将服务用量统一放在 usage_metadata。
    usage = message.usage_metadata
    if usage is not None:
        # 字段分别表示本次输入、输出和总 Token 数。
        return {"inputTokens": usage["input_tokens"], "outputTokens": usage["output_tokens"], "totalTokens": usage["total_tokens"]}
    # 缺失时由页面显示“服务未返回”。
    return None


# 接口调用的业务入口：先裁剪，再调用一次模型，最后整理回答和统计。
# request 是 UsageRequest，包含 question、history 和 contextBudget。
# 返回字典，包含回答、实际用量、耗时、粗估值、裁剪条数与结束原因。
# 配置缺失、认证失败或回答无效时抛出业务异常，其他异常交给脚手架。
async def chat(request):
    # 直接读取配置，不依赖聊天记忆业务。
    if not settings.bailian_api_key.strip():
        # Key 缺失时不创建客户端或调用模型。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "还没有配置百炼 API Key，请检查后端配置")
    # 请求历史是普通数据对象，先转换成 LangChain 消息。
    history = []
    for item in request.history:
        # user 表示用户提出的问题。
        if item.role == "user":
            # 将用户正文包装成用户消息。
            history.append(HumanMessage(content=item.content))
        else:
            # 将 assistant 正文包装成模型消息，保留发言身份。
            history.append(AIMessage(content=item.content))
    # 按顺序接收三个返回值：发送列表、移除条数、发送列表的粗估大小。
    messages, removed, estimated = build_context("你是一位数码商城助手，简洁回答用户的问题。", history, request.question, request.contextBudget)
    model = get_chat_model()
    start = perf_counter()
    try:
        reply = await model.ainvoke(messages, temperature=0.7,
            extra_body={"enable_thinking": False, "max_tokens": 512})
    except AuthenticationError as exception:
        # 保留异常原因，向页面返回认证提示。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "百炼 API Key 无效，请检查配置") from exception
    # 收到回答立即结束计时，秒转换为毫秒，保留一位小数。
    elapsed = round((perf_counter() - start) * 1000, 1)
    # 空白或非文字结果不作为成功回答返回。
    if not isinstance(reply.content, str) or not reply.content.strip():
        # 保留页面输入，提示重试。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "模型没有返回有效回答，请重试")
    # 返回本次结果，不累加之前调用的用量。
    return {
        # 模型返回的完整正文。
        "answer": reply.content,
        # 服务返回的真实 Token 数据，缺失时为 null。
        "usage": usage_from(reply),
        # 仅模型调用阶段的耗时，单位毫秒。
        "elapsedMs": elapsed,
        # 本地粗估值，不能用于核算实际费用。
        "estimatedInputTokens": estimated,
        # 移除的历史条数，每轮两条。
        "trimmedMessages": removed,
        # 消息总数减去 System 和本轮问题。
        "sentHistoryMessages": len(messages) - 2,
        # 统一转为大写；没有结束原因时显示 UNKNOWN。
        "finishReason": str(reply.response_metadata.get("finish_reason") or "UNKNOWN").upper(),
    }