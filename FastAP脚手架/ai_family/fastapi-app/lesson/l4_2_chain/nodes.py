"""统一模型调用及三个链式节点，返回局部状态更新供当前和后续工作流复用。"""
from typing import TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from settings import settings

# 本次图传递一份字典：入口先放 product，节点随后补入 points、copy、title。TypedDict 声明这些键的类型。
# StateGraph 读取这个结构建立状态字段，但 TypedDict 不会像 Pydantic 那样在运行时检查资料长度和空白。
# total=False 允许各键暂时缺省，例如提取前没有 points；必需的 product 由请求校验和图入口赋值保证。
class CopyState(TypedDict, total=False):
    # 用户提交的原始商品事实；extract、draft、title 都会读取它核对资料，后续结果不覆盖这个字段。
    product: str
    # extract 提取的卖点文字，例如“主动降噪、最长30小时续航”；图合并该字段后供 draft 组织正文。
    points: str
    # draft 写出的完整商品介绍，title 据此生成标题，页面用它展示正文；它不是聊天消息列表。
    copy: str
    # title 节点写出的标题，与 points、copy 一起保留到最终响应，页面把它放在正文上方。
    title: str

# 单节点的统一模型入口：system 是当前任务要求，content 是本次商品原文或拼入上游产物的资料字符串。
# 先检查 Key，再复制调用参数、发送两条消息、检查完整响应，最后返回 str；不在这里返回 State 或调用下一节点。
# Key 缺失、网络请求失败、正文无效或截断时向外抛异常，图不会沿正常边继续后继节点。
async def ask(system: str, content: str) -> str:
    # Key 只在后端检查和使用，不能放到 State 或返回结果中。
    if not settings.bailian_api_key.strip():
        # 配置错误先于模型请求返回，避免发送无效远程调用。
        raise CustomException(ResultCodeEnum.PARAM_ERROR, "请先配置百炼 API Key")
    # get_chat_model() 取得已有客户端，沿用模型名、地址和 Key；model_copy 为本次请求复制下面的参数。
    # update 是字段名到新值的字典，只覆盖列出的生成选项，不会修改其他请求共用的原客户端。
    model = get_chat_model().model_copy(update={
        # 较低温度减少措辞波动，不代表事实正确性已验证。
        "temperature": 0.2,
        # 本例每节点输出简短，限制为1024个输出Token，截断会被下方检查拒绝。
        "max_tokens": 1024,
        # 百炼透传参数关闭思考模式，节点只处理普通正文。
        "extra_body": {"enable_thinking": False},
    })
    # 这里 ainvoke 属于聊天模型：等待“一次模型请求”的完整响应，返回含 content 和 response_metadata 的消息对象。
    # await 允许事件循环在等待网络时处理其他任务，但当前节点尚未完成，后继节点仍须等它返回并合并更新。
    # service.py 中 app.ainvoke 属于可执行图，等待的是整张图，不能把两个同名方法当作同一层调用。
    response = await model.ainvoke([
        # SystemMessage 放当前任务加统一事实约束，要求模型不编造资料；这是提示词约束，不是程序已核验事实的保证。
        SystemMessage(content=system + "。只使用给定商品事实，不编造价格、折扣、销量或功效。"),
        # HumanMessage 放当前资料：提取时是 product，写正文时是 product 加 points，写标题时是 product 加 copy。
        # 每次只发送这里的两条消息，不读取或自动携带以往对话。
        HumanMessage(content=content),
    ])
    # 三种情况任一成立就失败：不是字符串、去掉首尾空白后无文字、结束原因是 length（达到输出长度上限）。
    # or 从左到右短路，非字符串时不会继续调用 strip；get 在没有 finish_reason 时返回 None，不报键缺失。
    # 拒绝截断内容，避免正文只生成半段，标题节点却把它当成完整介绍继续处理。
    if not isinstance(response.content, str) or not response.content.strip() or response.response_metadata.get("finish_reason") == "length":
        # 公共异常处理给页面明确失败提示，不继续生成虚假的成功状态。
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "节点输出为空或被截断，请缩短商品资料后重试")
    # 原样返回文本，由业务节点决定写入哪个State字段。
    return response.content

# 卖点节点：state 是图传入的当前字典，必须含用户原资料 product；本节点只执行一次卖点提取。
# 返回 {"points": 卖点字符串} 这项局部更新，图保留 product 并合并 points，然后才进入 draft。
# 缺少 product 或 ask 失败时异常向外传播，不返回固定卖点伪装成成功。
async def extract(state: CopyState) -> dict:
    # 第一个参数限定提取任务，state["product"] 作为第二个参数提供原始事实，await 等待卖点字符串。
    # 直接按键读取会在入口漏传 product 时暴露 KeyError，不用空串隐藏调用错误。
    points = await ask("从商品资料提取三条真实卖点，简洁列出", state["product"])
    # 左侧 "points" 是状态字段名，右侧 points 是模型文字；返回一项更新而不是直接修改传入 state。
    # 原状态只有 product 时，合并后同时含 product 和 points，draft 才能读取二者。
    return {"points": points}

# 正文节点：读取 product 与 extract 已生成的 points，把原事实和卖点合在一起交给模型写介绍。
# 返回 {"copy": 正文字符串}；图保留已有字段并加入 copy，title 要等这项更新完成后才执行。
# 必需字段缺失、模型调用或响应检查失败时中断，不把前一个节点产物当成完整正文返回。
async def draft(state: CopyState) -> dict:
    # + 把商品原文、换行标签、卖点文字拼成一个输入字符串；\n 发给模型时是真实换行。
    # points 是整理结果，可能遗漏条件，因此仍保留 product 供模型对照具体价格、功能和续航。
    content = state["product"] + "\n卖点：\n" + state["points"]
    # 只要求正文，不在本次调用中混入标题任务；“120字以内”是提示词要求，本例没有逐字统计的硬校验。
    copy = await ask("写一段不超过120字的商品介绍", content)
    # 只交回 copy；默认合并会替换同名字段，没返回的 product、points 保留，不必重新返回整份字典。
    return {"copy": copy}

# 标题节点：读取 product 和 draft 产生的 copy，生成一个与正文对应的标题，返回 {"title": 标题字符串}。
# 此节点不改正文；更新合并后走向 END，完整结果含 product、points、copy、title。
# ask 失败时整图失败，接口不会把只完成卖点、正文的状态当作完整成功结果。
async def title(state: CopyState) -> dict:
    # 标题仍同时参考原始资料，限制“为了吸引人而增加优惠”等虚构。
    content = state["product"] + "\n文案：\n" + state["copy"]
    # 任务要求只返回20字以内标题，content 提供原事实和完整正文；20字是提示词要求，代码未额外统计或截断字数。
    text = await ask("根据资料和文案只输出一个20字以内标题", content)
    # text 是标题字符串，用 title 字段交回图；不会覆盖 copy，页面能同时显示标题、正文和前面的卖点。
    return {"title": text}