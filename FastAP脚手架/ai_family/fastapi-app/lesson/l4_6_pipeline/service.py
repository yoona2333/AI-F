"""复用前面节点组合完整文案图，通过SSE推送真实节点开始、完成及最终结果。"""
import json
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from sse_starlette.sse import EventSourceResponse
from lesson.l4_2_chain.nodes import extract, title
from lesson.l4_3_route.nodes import xiaohongshu, douyin, wechat, route
from lesson.l4_6_pipeline.nodes import PipelineState, candidates, evaluate, optimize, next_step

# logger记录异常堆栈，页面只展示统一提示，不把凭证或内部配置发出去。
logger = logging.getLogger(__name__)

# 节点包装工厂：name 是节点注册名，action 是已有异步节点函数，返回内部 node 函数对象供 add_node 注册。
# 注册时不执行 action，也不获取 writer；图实际运行时由包装函数发送真实开始和完成进度，再原样交回业务更新。
def traced(name, action):
    # 包装后的实际异步节点：state 由图运行时传入，通过闭包取得 name 与 action。
    # 先写 started，await 原 action 得局部更新，再写 completed/output 并返回原更新；action 抛错时不发 completed。
    async def node(state):
        # 在当前图节点实际运行时获取 custom 流写入函数；它把字典交给 app.astream 的 custom 通道。
        # 不是直接写 HTTP 连接；外层生成器还要把它转换为 SSE step。离开图执行上下文就不能这样获取。
        writer = get_stream_writer()
        # 把真实开始信号写入 custom 通道：node 是注册名称，started 尚无 output，页面因此追加一个执行中记录。
        # 此时业务 action 还没返回，不能提前填入结果或宣称完成。
        writer({"node": name, "status": "started"})
        # action 是传给 traced 的已有异步业务函数，state 是图合并后的当前状态；真正执行原节点并等待局部更新。
        # 如果这里抛异常，不会执行下面 completed，外层发送 error；包装器没有吞错或补固定结果。
        update = await action(state)
        # 原节点已正常返回，才把同名 completed 和真实 update 写入 custom 通道；output 只是该节点返回值。
        # 页面匹配最近一个同名执行中记录，不能据此推断整张图已经完成，整图完成由 done 单独表示。
        writer({"node": name, "status": "completed", "output": update})
        # 把原节点局部更新原样交回 StateGraph 合并；writer 只增加进度消息，不承担合并，也没有改变原业务结果。
        return update
    # 返回内部函数对象，不是调用 node；add_node 保存该函数，图运行到这里才传入 state 执行。
    # 闭包保留本次传入的 name 和 action，所以同一包装方法能区分 extract、evaluate 等节点。
    return node

# SSE 编码辅助：name 是 step/done/error，data 是普通字典，返回响应库接受的 event/data 描述。
# 只将数据编码成 JSON 字符串，未直接发送 HTTP；字典须能 JSON 序列化，编码错误向外抛出。
def event(name, data):
    # 返回 SSE 库要求的描述字典：event 是事件名，data 必须是 JSON 字符串；真正发送由外层响应库负责。
    # ensure_ascii=False 保留中文，separators 压缩分隔空格；正文内的换行由 JSON 转义，不会被误认为 SSE 帧分隔。
    return {"event": name, "data": json.dumps(data, ensure_ascii=False, separators=(",", ":"))}

# 输入 ChannelRequest 对象，先注册组合图，再返回 EventSourceResponse；实际图执行在响应库消费 events 时开始。
# 正常按 step 发节点进度，完整结束且有最终标题后发 done/result；执行、解析或输出检查失败发 error，不发 done。
# 返回响应对象不是返回最终文案，本次状态只在当前执行中使用，不查询历史或保存运行记录。
def stream(request):
    # 用 PipelineState 声明本图可保存的字段结构；它包含入口输入及本图会产生的结果，节点返回字典后按键合并。
    # 这里只创建结构描述，不是创建数据库表或开始执行；每次请求的初始数据在调用执行方法时另行传入。
    graph = StateGraph(PipelineState)
    # 注册图内名称 extract 对应的任务：读取 product 原资料，调用提取任务，返回 points 卖点文字。
    # draft 或渠道写作节点需要 points，因此必须先完成提取并合并结果；这里只注册处理函数，尚未调用模型。
    # traced 先返回包装函数，实际执行时再在原节点前后写 started/completed，原返回值仍交图合并。
    graph.add_node("extract", traced("extract", extract))
    # 注册图内名称 xiaohongshu 对应的任务：读取商品与卖点，按小红书表达要求返回 copy。
    # 只在 channel=xiaohongshu 时由条件边选中，不同时执行其他渠道；这里只注册处理函数，尚未调用模型。
    # traced 先返回包装函数，实际执行时再在原节点前后写 started/completed，原返回值仍交图合并。
    graph.add_node("xiaohongshu", traced("xiaohongshu", xiaohongshu))
    # 注册图内名称 douyin 对应的任务：读取商品与卖点，按抖音口播表达返回 copy。
    # 只在 channel=douyin 时选中，产物仍是文字，不是视频；这里只注册处理函数，尚未调用模型。
    # traced 先返回包装函数，实际执行时再在原节点前后写 started/completed，原返回值仍交图合并。
    graph.add_node("douyin", traced("douyin", douyin))
    # 注册图内名称 wechat 对应的任务：读取商品与卖点，按公众号表达返回 copy。
    # 只在 channel=wechat 时选中；公共后继统一读取 copy，不需要区分上游渠道；这里只注册处理函数，尚未调用模型。
    # traced 先返回包装函数，实际执行时再在原节点前后写 started/completed，原返回值仍交图合并。
    graph.add_node("wechat", traced("wechat", wechat))
    # 注册图内名称 parallel 对应的任务：把父状态交给本节并行任务，内部并行生成并汇合择优。
    # 步骤条只记录一个 parallel 阶段，完成时三份候选和推荐都已产生，不表示内部顺序执行；这里只注册处理函数，尚未调用模型。
    # traced 先返回包装函数，实际执行时再在原节点前后写 started/completed，原返回值仍交图合并。
    graph.add_node("parallel", traced("parallel", candidates))
    # 注册图内名称 evaluate 对应的任务：读取当前 copy 与商品事实，返回 score、feedback、round 及 versions 快照。
    # 每进入一次就评估一版；条件边必须读本轮更新后的 score 和 round；这里只注册处理函数，尚未调用模型。
    # traced 先返回包装函数，实际执行时再在原节点前后写 started/completed，原返回值仍交图合并。
    graph.add_node("evaluate", traced("evaluate", evaluate))
    # 注册图内名称 optimize 对应的任务：读取当前 copy、feedback 和原商品事实，只返回新 copy。
    # 不能沿用旧分数判定新文案，下一条边必须回 evaluate 重新评分；这里只注册处理函数，尚未调用模型。
    # traced 先返回包装函数，实际执行时再在原节点前后写 started/completed，原返回值仍交图合并。
    graph.add_node("optimize", traced("optimize", optimize))
    # 注册图内名称 title 对应的任务：读取最终 copy 与原商品事实，生成 title。
    # 放在收尾位置，保证标题对应择优或优化后的实际正文；达到次数上限也要如实保留评分；这里只注册处理函数，尚未调用模型。
    # traced 先返回包装函数，实际执行时再在原节点前后写 started/completed，原返回值仍交图合并。
    graph.add_node("title", traced("title", title))
    # START 是虚拟入口，将本次初始状态先交给 extract；入口不请求模型，extract 返回更新后才向后推进。
    graph.add_edge(START, "extract")
    # 源节点 extract 已合并卖点后调用 route，route 从状态返回 channel；第三个参数把路由键映射为已注册节点名。
    # 例如 channel=xiaohongshu 只进入小红书；不是根据三个出边都执行，也不额外调用模型做分类。
    graph.add_conditional_edges("extract", route, {"xiaohongshu": "xiaohongshu", "douyin": "douyin", "wechat": "wechat"})
    # xiaohongshu 完成 copy 更新后交给公共 parallel；本次路由只激活一个渠道，因此不等待另两个未执行的渠道。
    graph.add_edge("xiaohongshu", "parallel")
    # douyin 完成 copy 更新后交给公共 parallel；本次路由只激活一个渠道，因此不等待另两个未执行的渠道。
    graph.add_edge("douyin", "parallel")
    # wechat 完成 copy 更新后交给公共 parallel；本次路由只激活一个渠道，因此不等待另两个未执行的渠道。
    graph.add_edge("wechat", "parallel")
    # parallel 阶段已完成三候选和择优，返回的 copy 是真实选中的候选原文；合并父状态后才交给 evaluate 打分。
    graph.add_edge("parallel", "evaluate")
    # 在 evaluate 更新已合并后调用 next_step，读取本轮 score 与 round；第三个参数把 done/retry 翻译为后继位置。
    # retry 进入 optimize，done 进入终点或最终标题；达到三版上限也走 done，不能把该路由键解释为质量达标。
    graph.add_conditional_edges("evaluate", next_step, {"done": "title", "retry": "optimize"})
    # 新 copy 合并后回到 evaluate 重新调用评分，生成新 score、feedback 和版本快照；不能给新文案沿用旧分数。
    # 这是循环回边，是否还允许下一次修改由 evaluate 后面的固定阈值和三版上限判断。
    graph.add_edge("optimize", "evaluate")
    # title 正常返回并合并更新后进入虚拟终点 END；执行到终点才表示整图正常结束，不会自动保存数据库。
    graph.add_edge("title", END)
    # 编译并检查前面注册的节点和连接，得到可执行图 app；这一步没有传入商品资料，也没有请求模型。
    # 真正执行在后面的 ainvoke 或 astream，图存在循环不代表框架自动知道业务次数上限。
    app = graph.compile()

    # 无参数的内部异步生成器，通过闭包读取 app/request，订阅 custom 节点消息及 values 完整快照。
    # custom 转为 SSE step，values 仅更新服务端最新 result；流正常结束检查最终标题后发 done。
    # 异常记后端堆栈并发 error，页面保留已完成步骤；网络结束本身不能代替业务 done。
    async def events():
        # 最后一次values是当前完整State，不把某个节点更新误当最终结果。
        result = None
        # 模型、JSON解析或图执行异常均停止，不再发送成功done。
        try:
            # astream返回图执行过程，不是模型逐字流；custom给节点事件，values给已合并State快照。
            async for mode, data in app.astream(
                # 初始只传本次商品与渠道，节点结果由图实际产生。
                {"product": request.product, "channel": request.channel},
                # 30是图步数保护，业务三版上限仍由next_step检查。
                config={"recursion_limit": 30},
                # 同时订阅两种模式，因此每项是(mode,data)，不是裸字典。
                stream_mode=["custom", "values"],
            ):
                # custom由traced中的writer产生，直接作为step发给页面。
                if mode == "custom":
                    # 将 custom 的节点字典封装为 SSE step；data 有 node/status，completed 时才有 output。
                    # yield 交出当前事件后生成器还会继续，页面可立即更新进度，不必等待整图结束。
                    yield event("step", data)
                # values在节点合并后更新，始终保留最后一个快照。
                elif mode == "values":
                    # values 的 data 是图合并后的完整状态快照，覆盖 result 以保留最新一次；不是某个节点的局部 output。
                    # 不立即把内部快照发给页面；流正常结束且最终字段检查通过后才用 done 发布最终结果。
                    result = data
            # 没有最终标题说明图未完整产出，不发送伪造的完成状态。
            if not result or not result.get("title"):
                # 进入统一错误分支，页面保留已经完成的步骤。
                raise ValueError("工作流没有完整结果")
            # 仅当图流正常遍历结束且最后状态含 title，才发送 done 携带最终 result；不表示入库或质量必然达标。
            # 发送后生成器结束；网络断开不等于已收到这个业务完成事件，页面必须单独检查。
            yield event("done", {"result": result})
        # 网络和模型错误的具体堆栈仅保留后端。
        except Exception:
            # logger.exception自动附带当前异常堆栈，供排查真实失败节点。
            logger.exception("工作流执行失败")
            # 已发的步骤保留，不能把部分结果当成成功完成。
            yield event("error", {"message": "工作流执行失败，请检查后端日志"})

    # events() 创建异步生成器，响应库消费它时才启动 app.astream 并执行节点；返回响应对象不等于图已完成。
    # send_timeout=30 限制慢连接的发送等待，不是整张图或单次模型生成必须在30秒内结束。
    return EventSourceResponse(events(), send_timeout=30)