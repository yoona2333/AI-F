import json
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from pydantic import ValidationError
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.l2_2_manual_tool.schemas import WeatherArguments
from lesson.l2_2_manual_tool.weather import get_weather
from settings import settings

# 工具定义只说明名称、用途和参数；这里没有注册自动执行器。
WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的模拟天气；需要用户提供城市名称。不是实时天气。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "用户明确提供的城市名称，例如杭州，不能猜测"},
            },
            # city 是必填字段。
            "required": ["city"],
            # 不允许额外参数。
            "additionalProperties": False,
        },
    },
}


def answer_text(message) -> str:
    # 输出达到上限时单独提示，不把截断回答报告为成功。
    if message.response_metadata.get("finish_reason") == "length":
        # 请用户调整问题后再试。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "模型输出达到上限，请缩短问题后重试")
    # 正文必须是非空字符串，不能继续提出工具请求。
    if message.tool_calls or not isinstance(message.content, str) or not message.content.strip():
        # 不把不完整输出当作成功回答。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "模型没有返回有效回答，请重试")
    # 原样保留 Markdown，页面负责渲染。
    return message.content

# 接收问题，最多请求模型两次；返回 answer 与实际执行的 toolCalls。
async def chat(question: str) -> dict:
    # 未配置 Key 时直接返回提示。
    if not settings.bailian_api_key.strip():
        # 不调用外部模型，也不向页面暴露配置。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "请先配置百炼 API Key")
    # 创建本次独立上下文，不保存其他请求的内容。
    messages = [
        # 规则说明工具用途、缺少城市先询问，以及模拟结果不能伪装成实时天气。
        SystemMessage(content="查询天气时使用 get_weather。用户未提供城市时先询问，不要猜测城市。工具返回模拟数据，回答必须说明非实时天气，不补充未经查询的信息。"),
        # 本轮用户问题放在规则之后。
        HumanMessage(content=question),
    ]
    # 复用已有同步客户端，不修改其共享属性。
    model = get_chat_model()
    # bind_tools 只将说明绑定到请求；没有传入 Python 函数，不会自动执行。
    model_with_tools = model.bind_tools([WEATHER_TOOL], tool_choice="auto")
    # 第一次异步请求，让模型选择工具或直接回答。
    first = await model_with_tools.ainvoke(
        messages,
        temperature=0,
        extra_body={"enable_thinking": False, "max_tokens": 512},
    )

    if first.response_metadata.get("finish_reason") == "length":
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "模型输出达到上限，请缩短问题后重试")
    if first.invalid_tool_calls:
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "工具参数无效，请提供城市名称")
    if not first.tool_calls:
        return {"answer": answer_text(first), "toolCalls": []}


    messages.append(first)


    tool_calls = []
    # 处理第一次响应里的全部调用；不循环请求新的模型决策。
    for call in first.tool_calls:
        # 只允许本节提供的工具，并要求有用于结果配对的编号。
        if call["name"] != "get_weather" or not call.get("id"):
            # 未知工具或缺少编号时不执行函数。
            raise CustomException(ResultCodeEnum.PARAM_ERROR, "模型返回了无效的工具调用")


        try:
            # AIMessage.tool_calls 的 args 已经是字典，不再对它 json.loads。
            #用来**校验模型输出的工具参数** `model_validate()`：Pydantic v2 的方法，把模型返回的参数字典，按我们定义的字段规则校验 只给city
            arguments = WeatherArguments.model_validate(call["args"])
        except ValidationError:
            raise CustomException(ResultCodeEnum.PARAM_ERROR, "工具参数无效，请提供城市名称")
        result = get_weather(arguments.city)
        messages.append(ToolMessage(
            content=json.dumps(result, ensure_ascii=False),
            tool_call_id=call["id"],
        ))
        # 记录实际执行的工具，供页面展示。
        tool_calls.append({
            # 模型提供的调用编号。
            "toolCallId": call["id"],
            # 已经检查过的工具名称。
            "toolName": call["name"],
            # 转回普通字典，作为响应 JSON 对象。
            "arguments": arguments.model_dump(),
            # 刚才实际执行的函数结果。
            "result": result,
        })

    second = await model.ainvoke(
        messages,
        temperature=0,
        # 关闭思考模式，限制最终回答长度。
        extra_body={"enable_thinking": False, "max_tokens": 512},
    )
    # 返回有效正文与实际执行记录。
    return {"answer": answer_text(second), "toolCalls": tool_calls}