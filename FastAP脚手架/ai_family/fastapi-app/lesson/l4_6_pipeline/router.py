"""接收商品与渠道，返回真实节点开始、完成与最终结果的SSE事件流。"""
from fastapi import APIRouter
from lesson.l4_3_route.schemas import ChannelRequest
from lesson.l4_6_pipeline import service

# 本节使用独立前缀，前端以POST发送JSON到/stream。
router = APIRouter(prefix="/api/workflow/6")

# 注册 POST /api/workflow/6/stream，商品与渠道放 JSON 请求体；前端使用支持 POST 的 streamRequest 消费响应事件。
@router.post("/stream")
# 输入 ChannelRequest 对象，先注册组合图，再返回 EventSourceResponse；实际图执行在响应库消费 events 时开始。
# 正常按 step 发节点进度，完整结束且有最终标题后发 done/result；执行、解析或输出检查失败发 error，不发 done。
# 返回响应对象不是返回最终文案，本次状态只在当前执行中使用，不查询历史或保存运行记录。
async def stream(request: ChannelRequest):
    # service.stream只创建图和响应对象，异步节点将在响应库消费生成器时实际执行。
    return service.stream(request)