"""三个候选节点各写独立字段，汇合节点使用真实候选作结构化择优。"""
from typing import Literal
from pydantic import BaseModel, Field
from lesson.l4_2_chain.nodes import CopyState, ask

# 保留已有字段并增加三条独立候选，避免并行节点同写copy导致状态冲突。
class ParallelState(CopyState, total=False):
    # A 分支的完整文案，只由 a 写入；choose 和页面读取，不能与 B/C 共用 copy 作为并行输出键。
    candidateA: str
    # B 分支的完整文案，只由 b 写入；与 A/C 独立保存，汇合后供 choose 比较，不表示第二名。
    candidateB: str
    # C 分支的完整文案，只由 c 写入；完成顺序不固定，选择结果为 C 时再把这份原文作为最终 copy。
    candidateC: str
    # 模型选择的 A/B/C 标签，经过 Choice 校验后写入；程序据此查候选原文，页面据此标推荐，而不是另生成第四份。
    winner: str
    # Choice.reason 的推荐理由，供页面说明为何选择；正文仍从已有候选取，不能把理由当 copy。
    recommendation: str

# 校验模型返回的JSON：只有合法标签和非空理由才可以继续下游流程。
class Choice(BaseModel):
    # Literal 在解析模型 JSON 时只允许 A、B、C 这三个精确标签，缺失或返回 D 都会失败，不默认选 A。
    winner: Literal["A", "B", "C"]
    # 理由必填且长度至少1，说明推荐标准而不是承诺投放收益。
    reason: str = Field(min_length=1)

# 公共候选任务：state 提供 product 原资料和 points 卖点；key 是本分支独占的 candidateA/B/C，angle 是写作角度。
# 等待一次模型响应后返回 {key: 文案字符串}，图合并到对应候选字段；不修改传入 state，失败向图外传播。
async def candidate(state: ParallelState, key: str, angle: str) -> dict:
    # product 来自本次用户输入，points 是 extract 刚产生的卖点；用换行标签拼成一份资料供模型阅读。
    # 保留商品原文用于核对价格和功能，卖点帮助模型组织当前角度的表达重点。
    content = state["product"] + "\n卖点：" + state["points"]
    # 各分支在同一图层异步调用模型，不依赖其他候选生成结果。
    text = await ask(angle + "，写120字以内文案", content)
    # key 是调用方传入的 candidateA/B/C，作为字典真正的字段名；例如 key="candidateB" 时得到 candidateB 到正文的更新。
    # 只返回本分支一项，避免把其他尚未返回的候选清空，也不直接修改传入 state。
    return {key: text}

# 候选A：读取公共商品和卖点，调用 candidate 指定场景角度与 candidateA，返回独占字段更新。
# 不读 B/C 结果，没有先后依赖；await 等本分支，图可同时等待其他异步分支，失败向整图传播。
async def a(state: ParallelState) -> dict:
    # await等待本分支，图可同时调度b和c，不是先等A再进入B。
    return await candidate(state, "candidateA", "强调使用场景")

# 候选B：读取同一公共输入，以已知功能角度生成，返回 candidateB 更新；不是给 A 的结果继续加工。
# 独占输出字段避免并行写 copy 冲突，模型失败使本次流程不能返回完整推荐。
async def b(state: ParallelState) -> dict:
    # 输出键与A不同，因此默认覆盖型State不需要额外共享列表reducer。
    return await candidate(state, "candidateB", "强调商品已知功能")

# 候选C：读取同一公共输入，以选择建议和适用人群角度生成，返回 candidateC 更新。
# 不等待 A/B；完成先后由真实响应决定，异常向并行图传播。
async def c(state: ParallelState) -> dict:
    # 三分支都只读商品事实，完成先后可能变化，页面不应声称固定先后。
    return await candidate(state, "candidateC", "强调选择建议与适用人群")

# 汇合择优：输入必须含 product 及 A/B/C 三份全文，等待模型返回标签和理由，再用 Choice 校验。
# 返回 winner、recommendation、copy，copy 必须取自原候选；JSON 或标签无效就中断，不默认选A，不另写第四版。
async def choose(state: ParallelState) -> dict:
    # 标签与完整原文同时提供给模型，评选时仍对照商品事实。
    content = state["product"] + "\nA：" + state["candidateA"] + "\nB：" + state["candidateB"] + "\nC：" + state["candidateC"]
    # 要求只输出JSON对象，不使用Markdown围栏，便于校验为具体对象。
    text = await ask('从A/B/C选择忠于事实且清晰的版本。只输出JSON对象，格式为{"winner":"A","reason":"推荐原因"}', content)
    # text 是评选模型返回的 JSON 字符串；此方法先解析 JSON，再按 Choice 校验 winner 为 A/B/C、reason 长度至少1。
    # 成功得到 Choice 对象供下面用属性读取；格式或字段不合格会抛异常，中断整图，不默认推荐 A。
    choice = Choice.model_validate_json(text)
    # 将合法标签拼成真实状态键：例如 winner="B" 得到 candidateB，再取出该分支已有全文。
    # 这一步是普通字典读取，不再次请求模型，确保最终 copy 与页面被标为推荐的候选相同。
    copy = state["candidate" + choice.winner]
    # 一次返回三项局部更新：winner 供标记推荐，recommendation 解释选择，copy 是所选候选的实际全文。
    # 图保留 candidateA/B/C 和原商品，页面展示推荐理由及选中正文；copy 取的是原候选，不是理由文字。
    return {"winner": choice.winner, "recommendation": choice.reason, "copy": copy}