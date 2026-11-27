"""从商品资料提取卖点，三路并行生成候选，汇合后择优并返回最终状态。"""
from langgraph.graph import StateGraph, START, END
from lesson.l4_2_chain.nodes import extract
from lesson.l4_4_parallel.nodes import ParallelState, a, b, c, choose

# 输入 data 是本次初始状态字典，至少提供 product 原资料；每次固定先提取 points，再并行写三份候选并择优。
# 返回最终状态字典，包含 product、points、candidateA/B/C、winner、recommendation、copy；模型或解析异常向外传播。
async def run(data: dict) -> dict:
    # 用 ParallelState 声明本图可保存的字段结构；它包含入口输入及本图会产生的结果，节点返回字典后按键合并。
    # 这里只创建结构描述，不是创建数据库表或开始执行；每次请求的初始数据在调用执行方法时另行传入。
    graph = StateGraph(ParallelState)

    # 直接注册已有 extract 函数，每次运行都从 product 提取 points，由图决定提取完成后才启动三个候选。
    # 三个候选共享这一次提取的结果，提取失败时不会启动后面的生成任务。
    graph.add_node("extract", extract)
    # 注册图内名称 candidateA 对应的任务：读取准备好的商品与卖点，从使用场景角度生成 candidateA。
    # 独占 candidateA，不读取 B/C 输出；图在发散后可以与另两路同时执行；这里只注册处理函数，尚未调用模型。
    graph.add_node("candidateA", a)
    # 注册图内名称 candidateB 对应的任务：读取同一份准备状态，从已知功能角度生成 candidateB。
    # 独占 candidateB，不等 A 生成完，也不覆盖最终 copy；这里只注册处理函数，尚未调用模型。
    graph.add_node("candidateB", b)
    # 注册图内名称 candidateC 对应的任务：读取同一份准备状态，从适用人群与选择建议角度生成 candidateC。
    # 独占 candidateC，结果完成顺序由真实模型响应决定，不按字母决定；这里只注册处理函数，尚未调用模型。
    graph.add_node("candidateC", c)
    # 注册图内名称 choose 对应的任务：读取齐全的 candidateA/B/C，校验模型推荐标签，再返回 winner、recommendation、选中 copy。
    # 它必须等三路汇合，不能只拿第一份返回的候选就评选；这里只注册处理函数，尚未调用模型。
    graph.add_node("choose", choose)
    # START 是虚拟入口，将本次初始状态先交给 extract；入口不请求模型，extract 返回更新后才向后推进。
    graph.add_edge(START, "extract")
    # 从同一 extract 向 candidateA 增加发散边；A/B/C 都读取准备完成后的状态，不依赖彼此产物。
    # 本边没有把候选排成 A→B→C，评选必须在后面的汇合处等全部分支。
    graph.add_edge("extract", "candidateA")
    # 从同一 extract 向 candidateB 增加发散边；A/B/C 都读取准备完成后的状态，不依赖彼此产物。
    # 本边没有把候选排成 A→B→C，评选必须在后面的汇合处等全部分支。
    graph.add_edge("extract", "candidateB")
    # 从同一 extract 向 candidateC 增加发散边；A/B/C 都读取准备完成后的状态，不依赖彼此产物。
    # 本边没有把候选排成 A→B→C，评选必须在后面的汇合处等全部分支。
    graph.add_edge("extract", "candidateC")
    # 第一个参数是三路源节点列表，只有 candidateA、candidateB、candidateC 全部完成并合并更新，才进入 choose。
    # 第二个参数 choose 是已注册的评选节点名；这是等待全部的汇合边，不是“任一候选先到就评选”。
    graph.add_edge(["candidateA", "candidateB", "candidateC"], "choose")
    # choose 正常返回并合并更新后进入虚拟终点 END；执行到终点才表示整图正常结束，不会自动保存数据库。
    graph.add_edge("choose", END)
    # 编译并检查前面注册的节点和连接，得到可执行图 app；这一步没有传入商品资料，也没有请求模型。
    # 后面的 ainvoke 才提交当前资料，依次执行提取、三路并行和汇合评选。
    app = graph.compile()
    # app.ainvoke 执行整张图并等待最后合并状态，不是 ask 内部的一次模型请求；输入字段来自本次请求。
    # 节点和 JSON 校验出错会向外传播，不能把前几步产物包装为最终成功；返回状态只属于本次执行。
    return await app.ainvoke(data)