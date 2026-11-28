"""发现MCP工具并流式执行客服，完整回答保存后发送done；连接覆盖整次Agent运行。"""
import json
import logging
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.errors import GraphRecursionError
from sse_starlette.sse import EventSourceResponse
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.l1_4_memory.models import MemoryMessage
from lesson.l5_3_framework.service import summarize
from fastmcp import Client
from lesson.l6_5_client.service import MCP_URL
from lesson.l6_6_agent.adapter import adapt
from lesson.l5_5_assistant.tools import traced
from settings import settings

# 系统规则对应本轮发现的商城查询，历史只用于指代，当前状态必须由MCP工具取得。
RULES = "你是商城客服。商品价格库存、订单和物流必须调用对应工具查询。订单号从用户问题或历史明确取得，不猜测。根据实际观察回答，未找到时明确说明。信息足够就给出最终答案，不输出隐藏思考。"

# __name__是当前模块名，用于区分日志来源；logger.exception在异常分支记录完整堆栈，页面只收到统一提示。
logger = logging.getLogger(__name__)

# 历史读取函数：无输入参数，查询消息表并返回字典列表，每项含id、role、content，供页面恢复已保存问答。
# 不调用模型或工具；数据库异常向调用方传播，由普通HTTP入口的公共异常处理提示。
async def list_messages():
    # all选择全部记录，order_by("id")按自增编号升序恢复先后顺序，values只取页面所需三列并返回字典。
    # await等待查询完成；role为user/assistant表示发言者，content保留原始正文和Markdown，不在查询时转换HTML。
    return await MemoryMessage.all().order_by("id").values("id", "role", "content")

# SSE编码函数：name是tool/delta/done/error事件名，data是该事件负载字典，返回响应库消费的event/data描述。
# 仅编码而不直接写网络；data含不能JSON编码的对象时抛错，由外层生成器的异常分支处理。
def event(name: str, data: dict) -> dict:
    # event字段供前端按事件类型分发；data先用json.dumps转字符串，正文换行由JSON转义，ensure_ascii=False保留中文，separators去掉JSON字段之间的额外空格。
    # 返回字典随后由yield交给EventSourceResponse，响应库才添加SSE帧结构并发送。
    return {"event": name, "data": json.dumps(data, ensure_ascii=False, separators=(",", ":"))}

# 流式业务入口：question是ReactRequest校验后的本次问题，返回EventSourceResponse，不是最终回答字典。
# 先检查配置，再创建内部异步生成器；历史查询、模型调用和保存都在响应库消费生成器时发生。
# 生成器正常结束并保存问答后发done；图步数、工具、生成或保存失败发error，不发布成功结果。
def stream(question: str):
    # 在建立SSE前检查凭证，缺配置时仍由公共处理返回普通JSON错误。
    if not settings.bailian_api_key.strip():
        # 不建立一条注定失败的模型请求。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "请先配置百炼 API Key")

    # 内部异步生成器无形参，通过闭包读取外层question；每次yield交出一条SSE事件，恢复迭代后继续执行。
    # 此处定义函数不会执行函数体；下面events()创建生成器，EventSourceResponse消费它时才逐步运行。
    async def events():
        # 所有读取、生成和保存异常统一转成error，不将连接关闭当作成功。
        try:
            # 按-id降序先取最新最多20条ORM记录，仅供本轮模型上下文；GET历史接口另外读取全部已保存内容。
            rows = await MemoryMessage.all().order_by("-id").limit(20)
            # reverse原地反转rows，不返回新的消息列表；使取到的最近记录按较早发言在前的顺序进入模型。
            rows.reverse()
            # 列表推导式逐个读取row：role为user时建立HumanMessage，否则将已保存助手回答转成AIMessage。
            # 每条content仍是原始文字，messages是本次独立上下文列表，不把历史拼成一大段用户问题。
            messages = [HumanMessage(content=row.content) if row.role == "user" else AIMessage(content=row.content) for row in rows]
            # append把当前用户问题追加到历史末尾，例如最近历史有20条时，入口messages总长度为21。
            # 历史帮助识别“它”指哪一单；是否查询及实时状态仍由本轮Agent和工具决定。
            messages.append(HumanMessage(content=question))
            # 取得已有客户端并复制本次选项，保留连接地址、Key、模型名与超时，不修改共享对象。
            model = get_chat_model().model_copy(update={
                # 降低生成随机性，商品和订单事实仍以工具观察为依据。
                "temperature": 0.0,
                # 每次模型响应最多1024输出Token，不是整次Agent多轮调用的总Token数。
                "max_tokens": 1024,
                # True启用模型文字增量，下方messages模式才能逐步把本轮文本交给页面。
                "streaming": True,
                # extra_body把非思考模式选项透传给百炼兼容接口，行动读取结构化工具请求。
                "extra_body": {"enable_thinking": False},
            })
            # 连接必须持续到Agent结束，适配后的工具会在后续模型轮次继续使用此client。
            async with Client(MCP_URL) as client:
                # 先发现真实工具目录，不直接注册本地查询函数；连接失败时不启动模型循环。
                definitions = await client.list_tools()
                # 创建本次Agent：注册工具只描述允许能力，此时不执行工具，也不请求模型。
                agent = create_agent(
                    # model是本次开启流式输出的客户端副本。
                    model=model,
                    # 逐项适配本轮MCP目录；traced在协议调用前后写时间线，耗时包含本次MCP往返。
                    tools=[traced(adapt(item, client)) for item in definitions],
                    # 在已有规则后拼接本节历史规则，说明历史用于指代、实时事实仍需本轮查询。
                    system_prompt=RULES + "历史用于理解用户指代；当前商品、订单、物流仍以本轮工具查询为准。",
                )
                # 尚未收到完整状态时设None；随后只用最新values快照覆盖，结束后从中读取最终消息链。
                output = None
                # astream执行图并返回异步迭代器；async for等待下一份数据，一次数据到达便处理，不等整图结束。
                # 订阅多个模式时每项是(mode,data)：mode为通道名，data随通道分别是字典、二元组或完整状态。
                async for mode, data in agent.astream(
                    # 入口状态包含已恢复历史和当前问题，框架在运行中继续追加工具请求、观察与助手消息。
                    {"messages": messages},
                    # 12限制图计算步数，包含模型和工具节点推进，不等于12秒或12次工具调用。
                    config={"recursion_limit": 12},
                    # custom接工具包装器通知，messages接模型文字增量，values接合并后的完整状态快照。
                    stream_mode=["custom", "messages", "values"],
                ):
                    # 工具消息原样封装；同名工具可能同时执行，页面按独立id匹配。
                    if mode == "custom":
                        # data就是traced内writer写入的字典；event编码为tool帧，yield交给响应库后前端按id更新卡片。
                        # yield只交出当前事件，生成器恢复后继续等待后续模型或工具数据，不表示整次完成。
                        yield event("tool", data)
                    # 模型文字增量用于当前草稿区，工具参数增量不作为自然语言显示。
                    elif mode == "messages":
                        # messages模式的data是(chunk,metadata)二元组，用解包分别取得文字块对象与图执行元数据。
                        # metadata中的langgraph_step标识该模型调用所在图步，供页面识别是否切换到新的生成轮次。
                        chunk, metadata = data
                        # and从左往右短路：先确认助手增量类型，再确认content是字符串，最后排除空串。
                        # 这里只取可显示的文字content，不把工具参数增量当作自然语言正文。
                        if isinstance(chunk, AIMessageChunk) and isinstance(chunk.content, str) and chunk.content:
                            # delta负载中step供页面分轮，text只是本次新增文字；get缺字段时返回None，不读取隐藏推理内容。
                            # 页面在step变化时清空前轮草稿，再累加本轮text；最终仍以done.answer为准。
                            yield event("delta", {"step": metadata.get("langgraph_step"), "text": chunk.content})
                    # values通道是图已合并状态，不把它逐份当最终结果发送。
                    elif mode == "values":
                        # values的data含图已合并的完整messages，不是某个工具的局部更新；仅覆盖output，不直接发送给前端。
                        output = data
                # 正常遍历结束后，output["messages"]包含入口历史、当前问题及本轮新增的AI/工具消息。
                # [len(messages):]从入口消息数量对应的下标取到末尾，例如入口21条时用[21:]跳过它们，仅保留新增消息。
                # 切片不删除原列表；若未收到output则交空列表，summarize会拒绝缺少完整回答的结果。
                # summarize核对最终答案与工具请求/观察是否匹配，返回answer/completed/steps，不再次调用模型。
                result = summarize(output["messages"][len(messages):] if output else [])
            # create等待一条数据库写入完成；先以user发言者保存本轮question原文，不保存拼接了历史的messages。
            await MemoryMessage.create(role="user", content=question)
            # 以assistant发言者保存summarize确认的最终Markdown原文；草稿、工具参数与观察不写入问答表。
            await MemoryMessage.create(role="assistant", content=result["answer"])
            # 两次await正常返回才yield业务done，answer是最终完整原文，页面据此追加正式问答并清除临时区。
            yield event("done", {"answer": result["answer"]})
        # 图耗尽步数时不保存问答、不发送done。
        except GraphRecursionError:
            # 记录真实异常，用户收到明确未完成提示。
            logger.exception("MCP客服Agent达到图步数上限")
            # 已完成工具记录保留，连接结束仍是失败。
            yield event("error", {"message": "Agent 达到执行步数上限，尚未完成，请缩小问题范围"})
        # 模型、工具、历史读取及保存错误均在此结束本次事件流。
        except Exception:
            # 堆栈含定位信息，仅在后端日志查看。
            logger.exception("MCP客服Agent执行失败")
            # 本例按顺序保存，写入异常时以数据库实际记录为准，不承诺两次写入一起回滚。
            yield event("error", {"message": "本次问答未完成，请检查后端日志并重新读取历史"})
    # events()创建异步生成器对象，响应库消费时才执行其内部查询与图运行；return并不是最终回答已完成。
    # send_timeout=30单位为秒，限制向慢连接发送事件的等待，不限制整张图或单次模型必须30秒内生成完。
    return EventSourceResponse(events(), send_timeout=30)