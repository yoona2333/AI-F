"""根据当前问题检索资料，流式返回正文及真实来源。"""
import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from sse_starlette.sse import EventSourceResponse
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.l3_6_search.service import search
from lesson.l3_7_rag_prompt.service import RULES, UNKNOWN, build_prompt

# 具体异常保留在后端日志，不把服务凭证发给页面。
logger = logging.getLogger(__name__)

# 输入事件名称和普通数据对象，返回 EventSourceResponse 可发送的事件字典。
# 输入事件名（sources/delta/done/error）及普通字典，返回 SSE 库需要的事件字典；该函数只编码，真正发送由外层响应完成。
def event(name, data):
    # dumps 把字典编码成 JSON 文本，正文换行不会破坏 SSE 帧。
    # event 指定事件类型；data 转为 JSON 字符串，ensure_ascii=False 保留中文，separators 去掉多余空格，正文换行会被转义而不破坏帧。
    #**压缩 JSON，去掉多余空格**，减少传输体积。
    return {"event": name, "data": json.dumps(data, ensure_ascii=False, separators=(",", ":"))}

# 输入本轮问题、TopK 和阈值，先检索证据，再返回 EventSourceResponse 响应对象。
# 内部生成器先发送正文 delta，结束后发送 sources 和 done；模型或输出检查失败时发送 error。
# 每次只发送固定规则和当前携带证据的问题，返回响应对象不代表模型已经生成完正文。
async def stream(request):
    # 当前完整问题直接检索，本节不做 Query 改写。
    # 把问题、TopK 和阈值交给 3-6，先拿真实来源列表，再决定是否调用聊天模型；sources 由后端检索产生。
    sources = await search(request)
    # 为本次请求新建消息列表，第一条 System 消息提供只依据资料回答的固定规则。
    messages = [SystemMessage(content=RULES)]
    # 当前问题携带本轮实际命中资料，不使用前一次的来源列表。
    # 把本次完整问题和本次检索资料放入唯一的用户消息，编号与来源卡片一致。
    messages.append(HumanMessage(content=build_prompt(request.question, sources)))
    # 来源说明由程序生成，生成成功后追加到当前回答末尾，便于对应来源卡片。
    # 有命中才初始化来源标题，没命中使用空串；编号与 Prompt、卡片一致，正文末尾展示同一份真实引用。
    footer = "\n\n来源：\n" if sources else ""
    # 编号顺序同时用于 Prompt、当前来源卡片与正文附注。
    # 按同一列表从 1 编号，保证来源附注与 Prompt 和页面卡片中的 [1] 指同一片；它不是数据库主键。
    for index, source in enumerate(sources, start=1):
        # 片段主键来自本轮检索，重切后编号可能变化，核对时以当前来源为准。
        # 逐条拼接文件名、文档内片段序号及真实主键；这些字段直接来自本轮来源，不由模型编写文件名。
        footer += f'- [{index}] {source["originalName"]}，片段 {source["chunkIndex"]}，编号 {source["id"]}\n'

    # 无输入参数的内部生成器，逐次产生事件；它由 EventSourceResponse 消费。
    # 内部异步生成器不接受参数，通过闭包读取本轮 sources/messages/footer；每次 yield 交出一个事件，并在后续继续执行。
    async def events():
        # 模型调用、结果检查或事件发送出错时只发送 error，不发送 done。
        try:
            # 累积完整正文，流结束时核对回答是否有效。
            # answer 累计模型正文，用来检查空回答；页面收到的 delta 仍然只包含每块新增文字。
            answer = ""
            # 没有证据时不调用聊天模型。
            # 空列表表示本次没有合格证据；进入固定答复分支，不调用聊天模型凭常识补商城规则。
            if not sources:
                # 使用固定、明确的无依据答复。
                answer = UNKNOWN
                # 固定答复也通过相同 delta 事件进入页面。
                yield event("delta", {"content": answer})
            else:
                # 复制为本次流式客户端，不改变其他课节的共享配置。
                # 取得已有客户端后复制本轮配置；不会修改其他请求共用的模型，update 字典只覆盖这里指定的参数。
                model = get_chat_model().model_copy(update={
                    # 启用流式模型响应，正文按增量读取。
                    "streaming": True,
                    # 减少表达随机性，仍需核对事实。
                    "temperature": 0.0,
                    # 限制本轮输出长度。
                    "max_tokens": 1024,
                    # 使用百炼非思考模式。
                    "extra_body": {"enable_thinking": False},
                })
                # 最后一个块可能只有结束原因，没有正文。
                finish_reason = None
                # astream 逐块产生结果，区别于一次等完整回答的 ainvoke。
                # astream 异步逐块返回模型响应，async for 等待下一块；chunk 可能含正文，也可能只含结束信息，不能假定每块都有字。
                async for chunk in model.astream(messages):
                    # 只处理有效字符串正文，不把元信息当内容。
                    # 只有 content 为非空字符串才当正文；and 短路检查，统计或结构化元数据不拼入回答。
                    if isinstance(chunk.content, str) and chunk.content:
                        # 累积完整正文供结束时检查。
                        # 将当前块追加到 answer，确保结束时检查的是完整正文，而不是最后一个可能没有文字的块。
                        answer += chunk.content
                        # 立即发出增量，页面追加并渲染 Markdown。
                        # delta 只携带这一块新增文字，前端用 += 追加；若每次发完整正文，页面也追加就会重复。
                        yield event("delta", {"content": chunk.content})
                    # 没有正文的最终块也要检查，才能识别截断。
                    # 用 get 读取可选结束原因，不存在不会报键错误；最后一块可能无正文，也必须执行这项检查。
                    if chunk.response_metadata.get("finish_reason"):
                        # 记录实际服务结束原因，不按字数猜测是否完成。
                        # 记录服务返回的实际停止原因，后面判断是否达到输出上限；不按收到的字数猜测是否完整。
                        finish_reason = chunk.response_metadata["finish_reason"]
                # 截断内容不能标记为成功问答。
                # length 表示输出因长度上限被截断；即使页面已经收到一些文字，也不标记回答完成、不发送 done。
                if finish_reason == "length":
                    # 进入下面错误事件处理，已显示的临时正文保留。
                    raise ValueError("回答未完成")
            # 即使没有报服务错误，也要拒绝空白正文。
            if not answer.strip():
                # 空白正文不能发送成功 done。
                raise ValueError("模型没有返回有效回答")
            # 有命中才追加真实来源说明，避免制造空引用。
            if footer:
                # 来源附注同样通过 delta 追加到页面已有正文。
                yield event("delta", {"content": footer})
            # 到这里正文完整且来源附注已发出，done 表示本次回答完整生成并且来源附注已经发送。
            # 正文及末尾来源附注均已发完，再让页面显示本轮参考来源卡片。
            yield event("sources", {"sources": sources})
            yield event("done", {"completed": True})
        # 不把模型或数据库失败伪装成完整完成。
        except Exception:
            # 具体异常只写后端日志。
            logger.exception("RAG生成失败")
            # 页面保留临时正文并显示错误，不会收到成功 done。
            yield event("error", {"message": "生成失败，请检查后端日志"})

    # SSE 帧编码和连接由库处理；页面按事件名识别来源、正文、完成与错误。
    # events() 创建异步生成器，此时并非已生成完回答；SSE 响应库消费它，将 yield 的字典编码成带事件名的帧并管理连接。
    return EventSourceResponse(events())