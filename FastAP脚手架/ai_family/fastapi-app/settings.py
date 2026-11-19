from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    app_name: str = "大模型应用开发"
    host: str = "0.0.0.0"
    port: int = 9091

    database_url: str = "mysql://root:000000@localhost:3306/ai_family"
    file_storage_path: Path = BASE_DIR.parent / "files"
    max_upload_size: int = 20 * 1024 * 1024

    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1" #默认的 API 地址，.env没有配置时使用
    bailian_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DASHSCOPE_API_KEY", "BAILIAN_API_KEY"),
    )
    bailian_chat_model: str = "qwen-plus"
    bailian_embedding_model: str = "text-embedding-v4"

    # 使用绝对路径读取 .env，不受启动目录影响
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
