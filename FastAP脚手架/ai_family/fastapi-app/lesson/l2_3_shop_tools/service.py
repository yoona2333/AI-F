import json
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.l2_3_shop_tools.tools import search_products, get_order
from settings import settings

SYSTEM = """你是商品与订单查询助手，使用中文简洁回答。
商品价格、库存和订单状态必须调用对应工具后回答；不猜测工具未提供的信息。
商品查询使用用户提供的名称关键词，订单号只能来自本次用户问题。
没有商品关键词或订单号时先询问，不编造编号，不擅自查询 DEMO1001。
用户同时问商品和订单时，分别调用对应工具。
products 为空或 found=false 时如实说明未找到，不生成一份记录。
所有查询结果都是模拟数据，最终回答必须说明非实时商城数据。"""


async def run_query(messages):
    if not settings.bailian_api_key.strip():
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "还没有配置百炼 API Key，请检查后端配置")


    model = get_chat_model().model_copy(update={
        # 决定回答的随机性和创造性
        "temperature": 0.2,
        "max_tokens": 1024,
        "extra_body": {"enable_thinking": False},
    })

    agent = create_agent(
        model=model,
        tools=[search_products, get_order],
        system_prompt=SYSTEM,
    )

    ''''{
        "messages": [
            HumanMessage(...),  # 用户消息
            AIMessage(...),  # 大模型回复（可能带 tool_calls）
            ToolMessage(...),  # 工具返回结果
            AIMessage(...),  # 最终回答消息
        ]
    }'''
    output = await agent.ainvoke(
        {"messages": messages},
        config={"recursion_limit": 8},
    )
    # output 是执行图返回的状态字典，output["messages"] 包含输入与本次新增的全部消息。
    # len(messages) 是输入消息条数，[len(messages):] 从输入之后截取到末尾，排除传入的用户问题。
    #Python 切片，**跳过前面输入的原始消息，只截取后面 Agent 新生成出来的消息**
    generated = output["messages"][len(messages):]
    # [-1] 读取新增消息的最后一条；正常结束时它应是模型根据工具结果生成的最终回答。
    final = generated[-1]

    if not isinstance(final, AIMessage) or final.tool_calls or not isinstance(final.content, str) or not final.content.strip() or final.response_metadata.get("finish_reason") == "length":
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "模型回答未完成，请缩小问题范围后重试")
    # requested 是临时字典：键是模型生成的调用 id，值是对应请求中的 name、args 等字段。
    # 同名工具可能被调用多次，所以必须按调用编号匹配，不能只按工具名匹配。
    requested = {}
    # calls 是最终返回页面的执行记录列表；只在读到对应工具结果消息后追加，不根据回答文字猜测。
    calls = []
    for message in generated:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                requested[call["id"]] = call
        elif isinstance(message, ToolMessage):
            # 框架可能把工具错误写进结果消息；status="error" 时正文不是本节正常的商品或订单结果。
            if message.status == "error":
                raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "工具执行失败，请检查后端日志和查询条件")
            call = requested[message.tool_call_id]
            # tools.py 用 json.dumps 把字典变成 JSON 字符串，这里用 json.loads 将结果正文还原成字典。
            result = json.loads(message.content)
            # 记录四个字段：原始调用编号、实际工具名、原请求参数字典和本次执行结果字典。
            # args 已是字典，content 才需要 loads；这两种数据不能用同一种方式重复解析。
            calls.append({"toolCallId": message.tool_call_id, "toolName": call["name"], "arguments": call["args"], "result": result})
    # answer 取最终模型消息的正文，toolCalls 取整理好的实际记录；没有调用工具时 calls 为空列表。
    return {"answer": final.content, "toolCalls": calls}



async def chat(question):
    return await run_query([HumanMessage(content=question)])