"""把已有知识库检索作为一个有参数约束的工具提供给模型。"""
import json
from typing import Annotated
from pydantic import Field
from langchain_core.tools import tool
from lesson.l3_6_search.schemas import RagSearchRequest
from lesson.l3_6_search.service import search

# 本工具接收模型提出的query，调用已有检索服务，返回{"sources": [...]}的JSON字符串。
# query的类型与长度由工具参数Schema检查，全空白还会被RagSearchRequest拒绝；异常沿工具执行链传播。
# @tool把函数名、下面的docstring和参数声明转换成模型可见的工具定义；注册时不请求Embedding或数据库。
@tool
# Annotated保留str类型，并附加Field长度约束；min_length/max_length单位为字符，不是Token。
async def knowledge_search(query: Annotated[str, Field(min_length=1, max_length=1000)]) -> str:
    """检索商城知识库中的售后、退换货、配送政策，返回相关原文片段及来源；无命中时返回空数组。"""
    # query来自本轮模型工具请求，映射到检索接口的question；topK最多返回3条，threshold过滤余弦分数小于0.3的片段。
    # RagSearchRequest先做输入校验，search随后才执行检索；实际命中可能不足3条或为空。
    request = RagSearchRequest(question=query, topK=3, threshold=0.3)
    # await等待问题向量化、片段相似度计算与筛选；hits是含content、originalName、score等字段的实际命中字典列表。
    hits = await search(request)
    # 把hits放进sources键并编码为字符串，框架将它写入ToolMessage，再作为观察交给下一轮模型。
    # ensure_ascii=False使中文保留原字符；hits为空时得到{"sources": []}，不是函数返回None。
    return json.dumps({"sources": hits}, ensure_ascii=False)