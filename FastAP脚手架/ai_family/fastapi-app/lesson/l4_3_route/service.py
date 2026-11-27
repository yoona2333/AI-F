"""按用户选择的渠道执行一个分支，再汇合到公共标题节点。"""
from langgraph.graph import StateGraph, START, END
from lesson.l4_2_chain.nodes import extract, title
from lesson.l4_3_route.nodes import RouteState, xiaohongshu, douyin, wechat, route

# 输入 request 是已校验的商品与渠道对象，建立含 product/channel 的初始状态；输出含卖点、所选渠道正文及标题的最终字典。
# 先提取再走一条渠道分支，最后公共标题；构图或节点异常向路由传播，不生成其他渠道备用结果。
async def run(request) -> dict:
    # 用 RouteState 声明本图可保存的字段结构；它包含入口输入及本图会产生的结果，节点返回字典后按键合并。
    # 这里只创建结构描述，不是创建数据库表或开始执行；每次请求的初始数据在调用执行方法时另行传入。
    graph = StateGraph(RouteState)
    # 注册图内名称 extract 对应的任务：读取 product 原资料，调用提取任务，返回 points 卖点文字。
    # draft 或渠道写作节点需要 points，因此必须先完成提取并合并结果；这里只注册处理函数，尚未调用模型。
    graph.add_node("extract", extract)
    # 注册图内名称 xiaohongshu 对应的任务：读取商品与卖点，按小红书表达要求返回 copy。
    # 只在 channel=xiaohongshu 时由条件边选中，不同时执行其他渠道；这里只注册处理函数，尚未调用模型。
    graph.add_node("xiaohongshu", xiaohongshu)
    # 注册图内名称 douyin 对应的任务：读取商品与卖点，按抖音口播表达返回 copy。
    # 只在 channel=douyin 时选中，产物仍是文字，不是视频；这里只注册处理函数，尚未调用模型。
    graph.add_node("douyin", douyin)
    # 注册图内名称 wechat 对应的任务：读取商品与卖点，按公众号表达返回 copy。
    # 只在 channel=wechat 时选中；公共后继统一读取 copy，不需要区分上游渠道；这里只注册处理函数，尚未调用模型。
    graph.add_node("wechat", wechat)
    # 注册图内名称 title 对应的任务：读取最终 copy 与原商品事实，生成 title。
    # 放在收尾位置，保证标题对应择优或优化后的实际正文；达到次数上限也要如实保留评分；这里只注册处理函数，尚未调用模型。
    graph.add_node("title", title)
    # START 是虚拟入口，将本次初始状态先交给 extract；入口不请求模型，extract 返回更新后才向后推进。
    graph.add_edge(START, "extract")
    # 源节点 extract 已合并卖点后调用 route，route 从状态返回 channel；第三个参数把路由键映射为已注册节点名。
    # 例如 channel=xiaohongshu 只进入小红书；不是根据三个出边都执行，也不额外调用模型做分类。
    graph.add_conditional_edges("extract", route, {
        # 小红书键对应同名节点。
        "xiaohongshu": "xiaohongshu",
        # 抖音键对应短视频节点。
        "douyin": "douyin",
        # 公众号键对应公众号节点。
        "wechat": "wechat",
    })
    # xiaohongshu 完成 copy 更新后交给公共 title；本次路由只激活一个渠道，因此不等待另两个未执行的渠道。
    graph.add_edge("xiaohongshu", "title")
    # douyin 完成 copy 更新后交给公共 title；本次路由只激活一个渠道，因此不等待另两个未执行的渠道。
    graph.add_edge("douyin", "title")
    # wechat 完成 copy 更新后交给公共 title；本次路由只激活一个渠道，因此不等待另两个未执行的渠道。
    graph.add_edge("wechat", "title")
    # title 正常返回并合并更新后进入虚拟终点 END；执行到终点才表示整图正常结束，不会自动保存数据库。
    graph.add_edge("title", END)
    # 编译并检查前面注册的节点和连接，得到可执行图 app；这一步没有传入商品资料，也没有请求模型。
    # 真正执行在后面的 ainvoke 或 astream，图存在循环不代表框架自动知道业务次数上限。
    app = graph.compile()
    # app.ainvoke 执行整张图并等待最后合并状态，不是 ask 内部的一次模型请求；输入字段来自本次请求或父图。
    # 节点和 JSON 校验出错会向外传播，不能把前几步产物包装为最终成功；返回状态只属于本次执行。
    return await app.ainvoke({"product": request.product, "channel": request.channel})