"""本节的渠道候选、汇合择优和评价优化任务；每项返回自己的局部状态更新。"""
import asyncio
from lesson.l4_2_chain.nodes import ask
from lesson.l4_4_parallel.nodes import ParallelState, Choice
from lesson.l4_5_review.nodes import ReviewState, Review

# 本节同时需要候选、版本快照和投放渠道；已有字段自然沿用，channel 在此处新增。
class PipelineState(ParallelState, ReviewState):
    # 来自本节 ChannelRequest 的已校验渠道键，写作、择优和评分都依据这个真实输入。
    channel: str

# 本节候选任务：state 含 product、points、channel 与已完成的渠道正文 copy；key 指定独占输出，angle 指定角度。
# 等待一次模型响应后返回 {key: 文案字符串}，图合并到对应候选字段；不修改传入 state，失败向图外传播。
async def candidate(state: PipelineState, key: str, angle: str) -> dict:
    # 原事实与卖点用于核对内容，channel 是本次投放渠道，copy 是选中渠道节点刚生成的基础正文。
    # 四项都是本图已产生的必需输入，直接按键读取，避免用空串掩盖遗漏的执行步骤。
    content = state["product"] + "\n卖点：" + state["points"] + "\n渠道：" + state["channel"] + "\n基础文案：" + state["copy"]
    # 各分支在同一图层异步调用模型，不依赖其他候选生成结果。
    text = await ask(angle + "，遵循给定渠道，改写基础文案，120字以内", content)
    # key 是调用方传入的 candidateA/B/C，作为字典真正的字段名；例如 key="candidateB" 时得到 candidateB 到正文的更新。
    # 只返回本分支一项，避免把其他尚未返回的候选清空，也不直接修改传入 state。
    return {key: text}

# 汇合择优：输入必须含 product、channel 及 A/B/C 三份全文，等待模型返回标签和理由，再用 Choice 校验。
# 返回 winner、recommendation、copy，copy 必须取自原候选；JSON 或标签无效就中断，不默认选A，不另写第四版。
async def choose(state: PipelineState) -> dict:
    # 标签与完整原文同时提供给模型，评选时仍对照商品事实。
    content = state["product"] + "\n渠道：" + state["channel"] + "\nA：" + state["candidateA"] + "\nB：" + state["candidateB"] + "\nC：" + state["candidateC"]
    # 要求只输出JSON对象，不使用Markdown围栏，便于校验为具体对象。
    text = await ask('从A/B/C选择忠于事实、清晰且符合给定渠道的版本。只输出JSON对象，格式为{"winner":"A","reason":"推荐原因"}', content)
    # text 是评选模型返回的 JSON 字符串；此方法先解析 JSON，再按 Choice 校验 winner 为 A/B/C、reason 长度至少1。
    # 成功得到 Choice 对象供下面用属性读取；格式或字段不合格会抛异常，中断整图，不默认推荐 A。
    choice = Choice.model_validate_json(text)
    # 将合法标签拼成真实状态键：例如 winner="B" 得到 candidateB，再取出该分支已有全文。
    # 这一步是普通字典读取，不再次请求模型，确保最终 copy 与页面被标为推荐的候选相同。
    copy = state["candidate" + choice.winner]
    # 一次返回三项局部更新：winner 供标记推荐，recommendation 解释选择，copy 是所选候选的实际全文。
    # 图保留 candidateA/B/C 和原商品，页面展示推荐理由及选中正文；copy 取的是原候选，不是理由文字。
    return {"winner": choice.winner, "recommendation": choice.reason, "copy": copy}

# 本节并行阶段：读取已提取的卖点和渠道正文，同时生成三个角度；不再次提取，也不调用4-4整图。
# 等三次任务全部返回后汇合为临时字典，择优只取已有候选；任一任务异常直接向外传播，不发送完成进度。
async def candidates(state: PipelineState) -> dict:
    # gather 同时启动三个候选协程，await 等全部结果；列表位置对应参数顺序，不取决于谁先返回。
    updates = await asyncio.gather(
        # A 从使用场景改写，独占 candidateA，所有任务只读同一份输入。
        candidate(state, "candidateA", "强调使用场景"),
        # B 从已知功能改写，不等 A 返回，独占 candidateB。
        candidate(state, "candidateB", "强调商品已知功能"),
        # C 从适用人群改写，独占 candidateC；完成顺序不影响择优标签。
        candidate(state, "candidateC", "强调选择建议与适用人群"),
    )
    # 复制当前状态到本方法局部字典，供择优同时读取原事实、渠道和候选，不直接改图传入的 state。
    combined = dict(state)
    # result 只累积本阶段产物，最终交给外层图合并；不重复返回未变化的商品或卖点。
    result = {}
    # updates 中每项只有自己的 candidate 键，逐项合并不会覆盖其他候选。
    for update in updates:
        # 临时状态补齐三候选，choose 随后才能读到完整对照集合。
        combined.update(update)
        # 记录本阶段要交回的三份候选，供页面展示。
        result.update(update)
    # 此时三份都已完成，才请求择优；返回 winner、recommendation 和所选原文 copy。
    selected = await choose(combined)
    # 把推荐信息与候选一起返回；这里的新 copy 将替换基础正文，供后续评价和标题使用。
    result.update(selected)
    # points 未重新生成，channel 未改动，外层图保留其原值并继续评价。
    return result

# 评价节点：state 至少含 product 与当前 copy，必须含 channel，上轮 round/versions 可缺省；先请求结构化评分。
# Review 校验后，版数加1，复制版本列表并追加当前正文及本次分数，返回 score、feedback、round、versions 四项。
# 不修改 copy；模型或 JSON 失败不记录伪造版本，异常中断图，不把半次评价当成功。
async def evaluate(state: PipelineState) -> dict:
    # 既评价表达也核对资料和渠道，不能只为堆营销词得到高分。
    # product 是原始事实，后面的标签和字段依次拼进同一条用户消息；\n 变成换行，帮助模型区分各段资料。
    # channel 由本节入口提供，直接读取并加入模型输入；缺失时暴露调用错误，而不是默认为无渠道。
    content = state["product"] + "\n渠道：" + state["channel"] + "\n文案：" + state["copy"]
    # 明确返回对象格式，不使用固定演示分数；评分依然可能随模型响应波动。
    text = await ask('评价文案的事实忠实、清晰度和渠道适配，0到100分。只输出JSON对象，格式{"score":80,"feedback":"具体建议"}', content)
    # 将评分模型的 JSON 字符串解析成 Review；score 要求严格整数0～100，feedback 要求非空字符串长度。
    # 字段缺失、分数为字符串或越界、JSON 不完整都会抛异常；不补一个固定80分让循环继续。
    review = Review.model_validate_json(text)
    # 首次评估没有 round，get 返回默认0，+1 得第1版；下一轮读取已合并的1，再得第2版。
    # 例如70→75→78分别对应 round=1、2、3，每版都必须先评分，第三版不合格也到停止上限。
    round_no = state.get("round", 0) + 1
    # 首次没有 versions 时以空列表为输入，后续读取上一轮列表；list(...) 浅复制列表容器，下面 append 不改旧容器。
    # 旧快照字典在这里仍共享引用，但代码只追加新字典，不修改旧项，避免前版正文和评分被后版覆盖。
    versions = list(state.get("versions", []))
    # 把本次刚评完的版本追加为新字典：round 是本版序号，copy 是此次评分对象，score/feedback 来自同一次响应。
    # 必须先记录当前正文再进入优化；不能把这一轮分数贴到尚未生成或尚未评价的新正文上。
    versions.append({"round": round_no, "copy": state["copy"], "score": review.score, "feedback": review.feedback})
    # 返回本轮四项更新，图合并后条件边读取对应的 score/round，optimize 读取 feedback，页面读取 versions。
    # copy 未在这里返回，当前已评正文仍保留；评分节点不偷偷替换正文。
    return {"score": review.score, "feedback": review.feedback, "round": round_no, "versions": versions}

# 优化节点：读取 product、copy、feedback 及 channel，按上一轮具体建议生成新文案。
# 只返回 copy 更新，不改 score、round、versions；下一条回边必须重新评价，新正文不能沿用旧分数。模型失败向外传播。
async def optimize(state: PipelineState) -> dict:
    # 原始资料始终保留，优化不是允许模型为了过分数自行增加事实。
    # product 是原始事实，后面的标签和字段依次拼进同一条用户消息；\n 变成换行，帮助模型区分各段资料。
    # channel 由本节入口提供，直接读取并加入模型输入；缺失时暴露调用错误，而不是默认为无渠道。
    # feedback 来自刚结束的评价，必须和当前 copy 一起发送，才能针对上一版问题修改，而不是盲目重写。
    content = state["product"] + "\n渠道：" + state["channel"] + "\n当前文案：" + state["copy"] + "\n改进建议：" + state["feedback"]
    # 只等待一段优化正文，不在这个节点内部无限重试。
    text = await ask("按建议优化文案，120字以内，只返回文案", content)
    # 下一步evaluate将为此版本生成新的score和快照。
    return {"copy": text}

# 退出判断：读取 evaluate 刚合并的 score 和 round，返回 done 或 retry 字符串供条件边映射。
# 分数>=80或评估版数>=3就停止，否则允许优化；只决定路径，不做模型请求，停止不一定代表达标。
def next_step(state: PipelineState) -> str:
    # 先看本轮分数是否>=80，或已评版本是否>=3；任一成立返回 done，否则返回 retry。
    # 例如第2版85分提前停止；第3版78分也停止但仍未达标。这里只返回路由键，不是宣布质量合格，也不改 State。
    return "done" if state["score"] >= 80 or state["round"] >= 3 else "retry"