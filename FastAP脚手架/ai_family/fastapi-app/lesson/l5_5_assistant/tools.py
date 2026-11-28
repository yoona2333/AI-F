"""在实际工具执行前后记录参数、结果和耗时，写入当前Agent的custom流。"""
from time import perf_counter
from uuid import uuid4
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

# 工具包装工厂：base是已有LangChain工具对象，包含name、description、args_schema以及可调用的ainvoke。
# 返回带相同名称、说明和参数结构的新工具；新工具执行时在原调用前后写进度，原结果仍返回给Agent。
# traced(base)只定义并返回包装工具，不立即执行查询；内部execute通过闭包记住本次传入的base。
def traced(base):
    # 内部异步任务接收本次工具参数，调用base.ainvoke，正常返回原结果；异常先写failed再继续抛出。
    # @tool将execute转换为工具对象：第一个参数保留原工具名称，description保留模型选择工具时阅读的用途说明。
    # args_schema沿用原参数模型，因此模型仍填写keyword/orderNo/query，而不是填写名为args的字段。
    @tool(base.name, description=base.description, args_schema=base.args_schema)
    # **args把传入的关键字参数收集为字典，例如orderNo="DEMO1001"成为{"orderNo": "DEMO1001"}。
    async def execute(**args):
        # 在Agent实际执行此工具时取得当前图的流写入函数；writer(dict)把数据交给custom通道，不直接发送HTTP。
        # 只能在图执行上下文取得writer；外层traced注册工具时尚无本次图运行，因此在这里获取。
        writer = get_stream_writer()
        # uuid4生成随机UUID，str转换为可JSON编码的字符串；每次工具执行各有一个id，页面据此匹配开始和结束。
        # 这个id用于本节时间线，不替代模型请求与ToolMessage之间的tool_call_id。
        record_id = str(uuid4())
        # perf_counter返回适合计时的秒数，记录起点，稍后相减；它不是日期时间或Unix时间戳。
        # 统计范围从此处到结束事件计算耗时，包含开始消息写入及原工具调用等待，不包含之前模型决策的时间。
        started = perf_counter()
        # 原工具尚未执行，先写started；外层生成器把此字典转成tool事件，页面追加执行中卡片。
        writer({
            # id关联这次执行前后两条消息，status决定页面追加还是更新卡片。
            "id": record_id, "status": "started",
            # name来自原工具注册信息，arguments是本次实际参数，不从回答文字猜测。
            "toolName": base.name, "arguments": args,
        })
        # 捕获本次工具异常，先通知时间线，再让Agent执行链处理失败。
        try:
            # 把参数字典交给原工具的ainvoke，继续执行原参数校验与查询；await等待本工具真正返回。
            # result仍是原工具返回值，供下面完成事件显示，并在return后由框架写成ToolMessage观察。
            result = await base.ainvoke(args)
        # 不把异常转换成成功结果或虚构观察。
        except Exception:
            # 当前秒数减started得到执行秒数，乘1000转毫秒，round(...,1)保留一位小数；failed不携带虚构result。
            writer({"id": record_id, "status": "failed", "durationMs": round((perf_counter() - started) * 1000, 1)})
            # 不带参数的raise重新抛出当前异常，后面的completed和return不会执行；外层也不会发送成功done。
            raise
        # 只有原调用正常返回才写completed；同一个record_id让页面更新已有卡片，result为原始观察，耗时同样为毫秒。
        writer({"id": record_id, "status": "completed", "result": result, "durationMs": round((perf_counter() - started) * 1000, 1)})
        # return交回原结果供框架形成ToolMessage；上面的writer仅通知页面，不能替代Agent所需的观察回传。
        return result
    # execute已被@tool转换为工具对象，返回该对象而非execute()调用结果；Agent选中它时才实际执行。
    return execute