
from secrets import randbelow
from langchain_core.messages import HumanMessage
from openai import APIStatusError, AuthenticationError, PermissionDeniedError
from common.exception_handler import CustomException
from common.result import ResultCodeEnum
from lesson.ll_1_chat.chat_model import get_chat_model
from lesson.ll_1_chat.schemas import SyncChatRequest, SyncChatResponse
from settings import settings


def chat(request: SyncChatRequest) -> SyncChatResponse:

    if not settings.bailian_api_key.strip():
        raise CustomException(
            ResultCodeEnum.SYSTEM_ERROR,
            "还没有配置百炼 API Key，请检查后端配置",
        )

    seed = randbelow(2147483647) + 1
    try:
        message = get_chat_model().invoke(
            [HumanMessage(content=request.question)],
            temperature=request.temperature,
            top_p=request.topP,
            seed=seed,
            extra_body={"enable_thinking": False, "max_tokens": request.maxTokens},
        )

    except AuthenticationError as exception:

        raise CustomException(
            ResultCodeEnum.SYSTEM_ERROR, "百炼 API Key 无效，请检查配置"
        ) from exception

    except PermissionDeniedError as exception:

        # 403：Key 本身有效，但没有该模型的调用权限
        raise CustomException(
            ResultCodeEnum.SYSTEM_ERROR,
            f"百炼 API Key 没有模型 {settings.bailian_chat_model} 的调用权限，请检查配置",
        ) from exception

    except APIStatusError as exception:

        # 其余上游错误（限流、参数不合法、服务不可用等）统一转成业务提示
        raise CustomException(
            ResultCodeEnum.SYSTEM_ERROR,
            f"调用百炼模型失败：{exception.status_code} {exception.message}",
        ) from exception

    # 读取响应元数据字典，模型名和结束原因保存在这里，正文在 content 中。
    metadata = message.response_metadata
    # 创建响应对象并返回，下面的字段组成页面需要展示的结果。
    return SyncChatResponse(
        # 把模型返回的回答正文保存到 answer。
        answer=message.content,
        # 优先读取元数据中的模型名；缺失或为空时回退到配置中的名称。
        modelName=metadata.get("model_name") or settings.bailian_chat_model,
        # 将当前请求的温度传给这次调用，不修改缓存客户端的属性。
        temperature=request.temperature,
        # 把本次请求的核采样值原样回传，供当前回答展示。
        topP=request.topP,
        # 把本次请求的最大输出 Token 数原样回传，供当前回答展示。
        maxTokens=request.maxTokens,
        # 取结束原因，缺失或为空时使用 UNKNOWN；转成字符串后统一大写。
        finishReason=str(metadata.get("finish_reason") or "UNKNOWN").upper(),
        # 本次调用的 token 用量；模型没返回时为 None。
        usage=message.usage_metadata,
    )