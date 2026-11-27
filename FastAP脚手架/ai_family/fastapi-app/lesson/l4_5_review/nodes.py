"""结构化评估与优化节点，保存本次运行的版本快照，固定最多评估三版。"""
from pydantic import BaseModel, Field
from lesson.l4_2_chain.nodes import CopyState, ask

# 继承正文状态，新增评分与本次版本列表，不使用聊天历史或持久化运行表。
class ReviewState(CopyState, total=False):
    # 本轮评价模型给出的整数分数，供条件边与页面读取；不是正确率或人工审核，不能保证事实正确。
    score: int
    # 本轮模型给出的具体修改建议，optimize 拼入下一次输入；只有分数没有建议就无法针对问题改写。
    feedback: str
    # 已经完成评估的版本数：初稿评完是1，两次修改评完最多3；不是修改次数或模型总调用数。
    round: int
    # 当前运行的版本快照列表，每项保留 round、copy、score、feedback，页面逐版显示对应正文与分数。
    versions: list[dict]

# 对模型JSON评分做类型及范围校验，不把“约80分”当作合法整数。
class Review(BaseModel):
    # strict=True 拒绝字符串"80"或小数，ge=0/le=100 要求整数落在包含两端的0～100；解析后供固定条件边判断。
    score: int = Field(strict=True, ge=0, le=100)
    # 本轮模型给出的具体修改建议，optimize 拼入下一次输入；只有分数没有建议就无法针对问题改写。
    feedback: str = Field(min_length=1)

# 评价节点：state 至少含 product 与当前 copy，可带上轮 round/versions；先请求结构化评分。
# Review 校验后，版数加1，复制版本列表并追加当前正文及本次分数，返回 score、feedback、round、versions 四项。
# 不修改 copy；模型或 JSON 失败不记录伪造版本，异常中断图，不把半次评价当成功。
async def evaluate(state: ReviewState) -> dict:
    # 既评价表达也核对原商品资料，不能只为堆营销词得到高分。
    # product 是原始事实，后面的标签和字段依次拼进同一条用户消息；\n 变成换行，帮助模型区分各段资料。
    content = state["product"] + "\n文案：" + state["copy"]
    # 明确返回对象格式，不使用固定演示分数；评分依然可能随模型响应波动。
    text = await ask('评价文案的事实忠实和清晰度，0到100分。只输出JSON对象，格式{"score":80,"feedback":"具体建议"}', content)
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

# 输入 product 原资料、copy 当前正文和 feedback 具体建议，按建议生成新文案。
# 只返回 copy 更新，不改 score、round、versions；下一条回边必须重新评价，新正文不能沿用旧分数。模型失败向外传播。
async def optimize(state: ReviewState) -> dict:
    # 原始资料始终保留，优化不是允许模型为了过分数自行增加事实。
    # product 是原始事实，后面的标签和字段依次拼进同一条用户消息；\n 变成换行，帮助模型区分各段资料。
    # feedback 来自刚结束的评价，必须和当前 copy 一起发送，才能针对上一版问题修改，而不是盲目重写。
    content = state["product"] + "\n当前文案：" + state["copy"] + "\n改进建议：" + state["feedback"]
    # 只等待一段优化正文，不在这个节点内部无限重试。
    text = await ask("按建议优化文案，120字以内，只返回文案", content)
    # 下一步evaluate将为此版本生成新的score和快照。
    return {"copy": text}

# 退出判断：读取 evaluate 刚合并的 score 和 round，返回 done 或 retry 字符串供条件边映射。
# 分数>=80或评估版数>=3就停止，否则允许优化；只决定路径，不做模型请求，停止不一定代表达标。
def next_step(state: ReviewState) -> str:
    # 先看本轮分数是否>=80，或已评版本是否>=3；任一成立返回 done，否则返回 retry。
    # 例如第2版85分提前停止；第3版78分也停止但仍未达标。这里只返回路由键，不是宣布质量合格，也不改 State。
    return "done" if state["score"] >= 80 or state["round"] >= 3 else "retry"