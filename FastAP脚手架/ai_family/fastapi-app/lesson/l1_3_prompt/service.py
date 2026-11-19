
from openai import AuthenticationError

from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.l1_3_prompt.prompts import PROMPTS
from lesson.l1_3_prompt.schemas import PromptChatRequest, PromptChatResponse
from settings import settings


# 展开角色模板，异步等待完整模型回答。
async def chat(request: PromptChatRequest) -> PromptChatResponse:
    """根据角色生成 system/human 消息，异步等待完整回答并返回实际提示词。"""
    # Key 为空时直接返回配置提示，不请求模型。
    if not settings.bailian_api_key.strip():
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "还没有配置百炼 API Key，请先完成配置")
    # Pydantic 已限制 role 范围，不会访问到不存在的模板。
    # invoke 在这里仅展开文本，并没有调用模型；to_messages 返回消息对象列表。
    #模板渲染完之后得到一个 `ChatPromptValue` 对象，调用 `.to_messages()`，转为 LangChain 的消息对象列表
    #model_dump()把 Pydantic 对象转成普通 python 字典
    messages = PROMPTS[request.role].invoke(request.model_dump()).to_messages()  # 包装成消息对象列表
    #模板的 `.invoke()`：填变量，只是字符串拼接           chat 模型的 `.invoke()`：真正发请求给大模型，拿到回答
    try:
        # ainvoke 发起一次模型请求，await 等待完整 AIMessage。
        answer = await get_chat_model().ainvoke(
            messages,
            # 固定温度，集中观察角色与变量的作用。
            temperature=0.7,
            # 固定核采样，与同步对话默认值一致。
            top_p=0.8,
            # 关闭思考模式；最大输出为 1024 Token，足够观察角色的简短回答。
            extra_body={"enable_thinking": False, "max_tokens": 1024},
        )
    # 认证失败时转换为页面可读的业务提示。
    except AuthenticationError as exception:
        raise CustomException(ResultCodeEnum.SYSTEM_ERROR, "百炼 API Key 无效，请检查配置") from exception
    return PromptChatResponse(
        answer=answer.content,
        role=request.role,
        modelName=answer.response_metadata.get("model_name") or settings.bailian_chat_model,                            
        systemPrompt=messages[0].content,
    )