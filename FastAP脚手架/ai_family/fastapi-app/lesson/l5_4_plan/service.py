"""规划一次、逐项查询商品、根据实际观察汇总建议。"""
import json
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.l2_4_shop_assistant.queries import search_products
from lesson.l5_4_plan.schemas import Plan
from settings import settings

# 输入本次商品对比问题，返回计划、已完成步骤与汇总答案；JSON校验、查询或模型失败均中断本次执行。
async def run(question: str) -> dict:
    # 凭证在模型调用前检查，不让缺少配置的问题进入后续查询。
    if not settings.bailian_api_key.strip():
        # 公共异常处理输出配置提示。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "请先配置百炼 API Key")
    # 本次两次生成使用同一客户端副本，规划和汇总均等待完整输出。
    model = get_chat_model().model_copy(update={"temperature": 0.0, "max_tokens": 1024, "streaming": False, "extra_body": {"enable_thinking": False}})
    # 固定JSON结构只允许商品关键词清单，模型不提供可执行代码。
    planning = [SystemMessage(content='为商品查询或对比生成1至3项查询计划。每项keyword是用户提到的商品名称或关键词，不编造型号，不重复。只输出JSON对象，格式为{"steps":[{"keyword":"耳机"}]}。'), HumanMessage(content=question)]
    # 第一次模型请求只负责规划，此时尚未查商品或生成价格结论。
    reply = await model.ainvoke(planning)
    # 完整字符串才交JSON解析，截断或工具请求都不是本例约定的计划。
    if not isinstance(reply, AIMessage) or not isinstance(reply.content, str) or reply.tool_calls or reply.response_metadata.get("finish_reason") == "length":
        # 失败时不会执行下面for循环。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "查询计划不完整，请重试")
    # JSON必须符合Plan结构和数量限制，不截取围栏、不补默认关键词；校验异常由公共处理返回失败。
    plan = Plan.model_validate_json(reply.content)
    # 只追加已经真实查询成功的步骤，作为汇总模型的观察和页面展示数据。
    steps = []
    # enumerate从1编号，严格按模型清单顺序执行，不在这里重新规划或并行调度。
    for index, item in enumerate(plan.steps, start=1):
        # 直接调用已有商品查询函数，函数校验关键词并返回products数组；空数组是正常业务结果。
        result = await search_products(item.keyword)
        # await正常返回才标completed，查询异常时立即向外传播，不补一份商品结果。
        steps.append({"index": index, "keyword": item.keyword, "status": "completed", "result": result})
    # 原问题和所有真实观察共同供汇总使用，空结果也保留，模型可说明哪些商品未查到。
    content = question + "\n实际查询记录：" + json.dumps(steps, ensure_ascii=False)
    # 第二次模型调用仅汇总已有结果，不新增商品、价格、库存或替用户执行购买。
    final = await model.ainvoke([SystemMessage(content="根据实际商品查询结果回答原问题，对比价格与库存并给出建议。只能使用记录中的事实；未查到的商品明确说明，无库存如实说明，不猜测优惠。"), HumanMessage(content=content)])
    # 只有完整非空文字才作为最终答案；不是模型请求成功就一定有有效回答。
    if not isinstance(final, AIMessage) or not isinstance(final.content, str) or not final.content.strip() or final.tool_calls or final.response_metadata.get("finish_reason") == "length":
        # 这时已有查询结果不包装为整次成功。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "汇总回答不完整，请重试")
    # plan是校验后的原清单，steps含实际观察；两个对象分别表示规划与执行，便于对应。
    return {"plan": plan.model_dump(), "steps": steps, "answer": final.content}