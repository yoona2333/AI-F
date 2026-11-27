"""接口调用本服务，注册三个任务与固定连接，执行本次链式图并返回最终状态字典。"""
from langgraph.graph import StateGraph, START, END
from lesson.l4_2_chain.nodes import CopyState, extract, draft, title

# 输入 product 是请求校验后的原始商品字符串；返回 dict，含 product、points、copy、title，供路由统一包装。
# 过程分为注册节点、连接执行顺序、编译结构、提交输入执行；前三步不请求模型。
# 构图错误、必需状态缺失或任一模型异常向外传播；不写数据库，也不把部分产物当作完整结果返回。
async def run(product: str) -> dict:
    # CopyState 描述四个状态字段，StateGraph 读取它建立更新通道；此时仅声明结构，未传入本次资料。
    # 各节点返回的局部字典按字段合并，没有自定义规则时同名字段由新值覆盖，未返回的字段保留。
    graph = StateGraph(CopyState)
    # "extract" 是图内名称，extract 是导入的函数对象；执行到该名称时，框架才调用 extract(state)。
    # 注册时不写 extract(...)，否则会提前尝试调用函数，失去由图传入状态和控制执行时机的作用。
    graph.add_node("extract", extract)
    # 注册正文函数，它需要 product 与 points；这一行只记录名称和函数的对应关系，并未执行写作。
    graph.add_node("draft", draft)
    # 注册标题函数，它需要 product 与 copy；注册的先后不是执行依赖，真正的顺序由下方边规定。
    graph.add_node("title", title)
    # START 是虚拟入口，不调用模型；这条边把初始状态先交给卖点节点，执行流程从这里开始。
    graph.add_edge(START, "extract")
    # extract 返回 points 后先合并更新，再进入 draft；正文因此能同时读取原 product 和新 points。
    graph.add_edge("extract", "draft")
    # draft 的 copy 合并后才运行 title，保证标题依据的是完整正文，不能把两者当独立任务并行。
    graph.add_edge("draft", "title")
    # title 更新合并后到达 END，结束本次图；END 不额外生成内容，也不自动保存数据。
    graph.add_edge("title", END)
    # compile 校验并编译连接结构，返回可执行图 app；得到 app 时三个模型节点都还没有运行。
    app = graph.compile()
    # 这里 ainvoke 属于可执行图，接收本次初始字典，只放 product，其他字段必须由节点逐步产生。
    # await 等 extract、draft、title 按边完成后，返回最终合并字典；不是 nodes.ask 中等待一次模型响应的 ainvoke。
    return await app.ainvoke({"product": product})