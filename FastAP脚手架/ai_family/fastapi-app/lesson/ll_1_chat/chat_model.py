from functools import lru_cache
from langchain_openai import ChatOpenAI
from settings import settings



# 缓存函数成功返回的对象；函数无参数，因此后续调用复用同一个客户端。
@lru_cache
# 首次调用时创建，后续复用；创建客户端本身不会向模型发送问题。
def get_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.bailian_base_url,
        api_key=settings.bailian_api_key,
        model=settings.bailian_chat_model,
        timeout=45,
        max_retries=0,
        streaming=False,
        use_responses_api=False,
    )