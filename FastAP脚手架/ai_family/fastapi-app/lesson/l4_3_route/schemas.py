"""继承商品资料校验，增加固定渠道；前端只能提交这三个已实现的路由键。"""
from typing import Literal
from lesson.l4_2_chain.schemas import CopyRequest

# 继承保留product及其空白校验，新增channel；不修改4-2的原请求对象。
class ChannelRequest(CopyRequest):
    # 用户选择的稳定渠道键：xiaohongshu/douyin/wechat；路由据此选节点，候选与评估也可据此读取表达要求。
    channel: Literal["xiaohongshu", "douyin", "wechat"]