"""提供三种渠道文案节点，条件边只选其中一个，再汇合到标题节点。"""
from lesson.l4_2_chain.nodes import CopyState, ask

# 继承已有字段结构，新增渠道；total=False允许图在分步运行时只有部分结果。
class RouteState(CopyState, total=False):
    # 用户选择的稳定渠道键：xiaohongshu/douyin/wechat；路由据此选节点，候选与评估也可据此读取表达要求。
    channel: str

# 渠道写作公共方法：state 必须已有 product、points，style 为当前渠道的固定表达要求。
# 等待一次 ask，返回 {copy: 文案字符串}，不决定选择哪个渠道、不生成标题；模型失败向图传播，公共后继不会正常执行。
async def write(state: RouteState, style: str) -> dict:
    # 原始资料和已提取卖点同时进入提示词，避免渠道表达覆盖事实条件。
    content = state["product"] + "\n卖点：" + state["points"]
    # 每个分支共用同一单节点调用入口，输出限制保持一致。
    text = await ask(style + "。写120字以内文案", content)
    # 三个分支虽写同一字段，但本节每次仅激活一个，不是同时写copy。
    return {"copy": text}

# 小红书分支：state 必须含商品和卖点，调用 write 时附加场景与卖点表达要求，返回 copy 更新。
# 只运行本分支，不调用另外两个渠道；ask 失败时中断，不能编造亲测体验作为商品事实。
async def xiaohongshu(state: RouteState) -> dict:
    # await等当前分支写作结束，其他渠道节点不会因此被调用。
    return await write(state, "小红书风格：使用场景加清晰卖点，不编造亲测体验")

# 抖音分支：输入本次商品和卖点，调用 write 指定问题开场、短句、自然收尾，异步返回 copy 更新。
# 输出是口播文字，不是视频；原事实保留，模型异常传播到图。
async def douyin(state: RouteState) -> dict:
    # 改变组织方式而非增加资料没有的价格或销量。
    return await write(state, "抖音口播风格：问题开场、短句说明、自然收尾")

# 公众号分支：输入本次商品和卖点，调用 write 指定解释式表达，返回 copy 更新给公共 title。
# 只改变表达方式，不添加优惠或未提供的功能；生成失败会中断后继。
async def wechat(state: RouteState) -> dict:
    # 同名copy使公共标题节点无需知道前面选中了哪个分支。
    return await write(state, "公众号风格：先说适用场景，再解释卖点与适用条件")

# 条件边判断函数：state 含请求校验后的 channel，返回该值作为路由键字符串，而不是更新字典。
# service 的映射再把键变为目标节点；不调用模型分类，不在此处生成正文。
def route(state: RouteState) -> str:
    # 从当前状态读取入口已校验的渠道值，返回的是路由键字符串，不是状态更新字典。
    # 例如 xiaohongshu 会被 service 的映射定位到同名节点；本函数不请求模型，也不生成文案。
    return state["channel"]