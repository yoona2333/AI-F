"""用条件边和回边实现有界评估—优化，不在节点函数里隐藏while循环。"""
from langgraph.graph import StateGraph, START, END
from lesson.l4_2_chain.nodes import extract, draft
from lesson.l4_5_review.nodes import ReviewState, evaluate, optimize, next_step

# 输入 product 是本次商品原文，生成初稿后开始评估；输出最终 copy、score、feedback、round、versions 及保留的商品卖点。
# 第一版即初稿，最多两次优化；到80或评完三版都结束，低分上限结果须如实返回，节点异常则中断并报错。
async def run(product: str) -> dict:
    # 用 ReviewState 声明本图可保存的字段结构；它包含入口输入及本图会产生的结果，节点返回字典后按键合并。
    # 这里只创建结构描述，不是创建数据库表或开始执行；每次请求的初始数据在调用执行方法时另行传入。
    graph = StateGraph(ReviewState)
    # 注册图内名称 extract 对应的任务：读取 product 原资料，调用提取任务，返回 points 卖点文字。
    # 本节 draft 正文节点需要 points，因此必须先完成提取并合并结果；这里只注册处理函数，尚未调用模型。
    graph.add_node("extract", extract)
    # 注册图内名称 draft 对应的任务：读取 product 与 points，生成正文并返回 copy。
    # 它只写初稿，不写标题或评分，后继按边读取 copy；这里只注册处理函数，尚未调用模型。
    graph.add_node("draft", draft)
    # 注册图内名称 evaluate 对应的任务：读取当前 copy 与商品事实，返回 score、feedback、round 及 versions 快照。
    # 每进入一次就评估一版；条件边必须读本轮更新后的 score 和 round；这里只注册处理函数，尚未调用模型。
    graph.add_node("evaluate", evaluate)
    # 注册图内名称 optimize 对应的任务：读取当前 copy、feedback 和原商品事实，只返回新 copy。
    # 不能沿用旧分数判定新文案，下一条边必须回 evaluate 重新评分；这里只注册处理函数，尚未调用模型。
    graph.add_node("optimize", optimize)
    # START 是虚拟入口，将本次初始状态先交给 extract；入口不请求模型，extract 返回更新后才向后推进。
    graph.add_edge(START, "extract")
    # extract 返回 points 后先合并，再执行 draft；后继因此同时拥有原 product 和卖点，顺序不是靠函数定义位置保证。
    graph.add_edge("extract", "draft")
    # draft 的 copy 合并后再进入 evaluate，使用的是本次已完成正文；如果正文失败，不沿这条正常边继续。
    graph.add_edge("draft", "evaluate")
    # 在 evaluate 更新已合并后调用 next_step，读取本轮 score 与 round；第三个参数把 done/retry 翻译为后继位置。
    # retry 进入 optimize，done 进入终点或最终标题；达到三版上限也走 done，不能把该路由键解释为质量达标。
    graph.add_conditional_edges("evaluate", next_step, {"done": END, "retry": "optimize"})
    # 新 copy 合并后回到 evaluate 重新调用评分，生成新 score、feedback 和版本快照；不能给新文案沿用旧分数。
    # 这是循环回边，是否还允许下一次修改由 evaluate 后面的固定阈值和三版上限判断。
    graph.add_edge("optimize", "evaluate")
    # 编译并检查前面注册的节点和连接，得到可执行图 app；这一步没有传入商品资料，也没有请求模型。
    # 真正执行在后面的 ainvoke 或 astream，图存在循环不代表框架自动知道业务次数上限。
    app = graph.compile()
    # app.ainvoke 执行整张图并等待最后合并状态，不是 ask 内部的一次模型请求；输入字段来自本次商品请求。
    # 节点和 JSON 校验出错会向外传播，不能把前几步产物包装为最终成功；返回状态只属于本次执行。
    # recursion_limit=20 是图运行步数保护，业务上限仍由 round>=3 决定，不能把20说成可修改20版。
    return await app.ainvoke({"product": product}, config={"recursion_limit": 20})