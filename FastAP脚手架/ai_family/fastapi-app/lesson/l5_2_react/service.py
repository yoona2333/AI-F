"""手动组织模型决策、工具执行、观察回传和退出，返回本次回答及真实工具记录。"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.l2_4_shop_assistant.tools import search_products, get_order, get_logistics
from settings import settings

# 这三个现有工具分别读取商品、订单和物流演示表；这里只声明当前允许选择的能力，不会立即执行查询。
TOOLS = [search_products, get_order, get_logistics]
# tool.name是向模型公布的准确名称，值是可执行工具对象；例如get_order映射到现有订单查询。
TOOL_MAP = {tool.name: tool for tool in TOOLS}
# 固定最多5次模型决策，最终回答也占一次；不是最多5次重试，也不是查询超时秒数。
MAX_ROUNDS = 5
# 模型只根据真实结果回答，完整订单号来自本次问题；缺信息可以向用户说明，不猜测编号或查询结果。
RULES = "你是商城查询助手。根据当前问题选择商品、订单或物流工具。每轮最多调用一个工具，取得结果后再决定下一步。订单号必须来自用户，不猜测编号。查询到的事实以本轮工具结果为准；未查到就明确说明。信息足够时直接给出最终回答，不再调用工具。不要输出隐藏思考过程。"

# 输入本次已校验问题字符串，独立创建消息列表，最多作5次决策并执行实际工具；不读取或保存历史。
# 返回answer、completed、steps；steps每项为round/toolName/arguments/result，完成表示模型已给出最终文字，不保证事实绝无遗漏。
# Key缺失、工具未知、参数错误、模型响应无效或工具执行异常时抛错，中断本请求；达到轮次上限则返回明确未完成结果。
async def run(question: str) -> dict:
    # Key来自服务端配置；全空白也视为缺失，先拒绝再创建请求，不把凭证放进页面或工具记录。
    if not settings.bailian_api_key.strip():
        # 公共异常处理生成明确提示，尚未请求模型或数据库。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "请先配置百炼 API Key")
    # 取已有客户端，复制当前需要的生成选项，不修改共享对象或重新配置连接地址。
    model = get_chat_model().model_copy(update={
        # 低温减少措辞变化，仍须核对最终回答和真实工具结果。
        "temperature": 0.0,
        # 每轮限制输出Token数，截断会在下面检查并中断，不能当完整工具请求继续。
        "max_tokens": 1024,
        # 本节等待每轮完整消息，页面收到的是整次结束后的结果，不作逐字推送。
        "streaming": False,
        # 百炼透传选项关闭思考模式；工具决策通过结构化tool_calls读取，不解析隐藏推理。
        "extra_body": {"enable_thinking": False},
    })
    # bind_tools把工具名称、说明和参数结构提供给模型，不会自动执行工具；parallel_tool_calls=False要求一轮最多一项行动。
    agent_model = model.bind_tools(TOOLS, parallel_tool_calls=False)
    # 每个请求新建上下文，第一条是固定规则，第二条是当前完整问题；用户要在本次明确提供订单号。
    messages = [SystemMessage(content=RULES), HumanMessage(content=question)]
    # 只保存本次真正执行过的工具记录；不是数据库历史，也不提前生成模型尚未选择的步骤。
    steps = []
    # range右端不包含，依次得到1、2、3、4、5，每次循环恰好请求模型作一次决策。
    for round_no in range(1, MAX_ROUNDS + 1):
        # 发送原问题及已经追加的请求/观察；await等待本轮完整AIMessage，不是自动执行完整Agent。
        reply = await agent_model.ainvoke(messages)
        # 非AI消息、参数解析失败或length截断均不能用于正常执行；or短路，类型不对时不继续读取其属性。
        if not isinstance(reply, AIMessage) or reply.invalid_tool_calls or reply.response_metadata.get("finish_reason") == "length":
            # 停止本请求，不尝试从残缺JSON猜参数，也不生成一条固定观察来掩盖失败。
            raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "模型工具请求无效或被截断，请重试")
        # 原样保留模型消息，里面含工具调用编号；后面ToolMessage必须接在对应请求之后。
        messages.append(reply)
        # tool_calls为空表示本轮没有请求工具，此时只有非空字符串正文才可作为最终回答。
        if not reply.tool_calls:
            # 不把空白或结构化元数据当成已经回答；and/or短路先保证字符串再调用strip。
            if not isinstance(reply.content, str) or not reply.content.strip():
                # 正常网络响应也可能没有有效正文，必须明确失败。
                raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "模型没有返回有效回答")
            # 返回模型本轮最终文字与已经执行的记录；本节不要求前端恢复旧问题或保存运行。
            return {"answer": reply.content, "completed": True, "steps": steps}
        # 请求参数已声明单工具模式，仍校验返回数量，避免一次响应执行不受本例限制的一批操作。
        if len(reply.tool_calls) != 1:
            # 这是模型返回不符合本节约定，不是让程序偷偷只执行第一项。
            raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "本例每轮只执行一个工具，请重试")
        # 取本轮唯一调用，LangChain已把原始参数JSON整理为args字典；本程序不靠正文中的工具名猜行动。
        call = reply.tool_calls[0]
        # 按准确名称在允许集合查找，get找不到时返回None；不能根据模型文字动态导入任意函数。
        tool = TOOL_MAP.get(call["name"])
        # 同时核对工具是否已注册及调用编号是否存在，保证后面的观察能对应原请求。
        if tool is None or not call.get("id"):
            # 未知工具或缺编号直接失败，尚未执行这次查询。
            raise CustomException(ResultCodeEnum.PARAM_ERROR, "工具名称或调用编号不合法")
        # ainvoke在这里属于工具对象：先按工具参数结构校验args，再调用已有异步查询，返回真实JSON文本。
        result = await tool.ainvoke(call["args"])
        # 记录实际执行信息；round是模型决策轮次，arguments来自本轮args，result来自数据库查询，不是模型编写的结果。
        steps.append({"round": round_no, "toolName": call["name"], "arguments": call["args"], "result": result})
        # 工具返回值放入ToolMessage，而非HumanMessage；本轮call.id将结果与对应AI工具请求关联起来。
        messages.append(ToolMessage(
            # content为工具已有的JSON字符串，例如found=false；保留它让下一轮基于真实观察继续判断。
            content=result,
            # 精确沿用本轮调用编号，不能把工具名称当作tool_call_id。
            tool_call_id=call["id"],
            # name标注返回结果的工具，与注册名一致，便于核对消息来源。
            name=call["name"],
        ))
    # 五次决策都请求工具而没有给出最终回答时才走到这里，不额外请求第六轮，不把最后观察伪装成答案。
    return {"answer": "已达到本例5轮决策上限，尚未生成最终回答。请缩小问题范围后重新提交。", "completed": False, "steps": steps}