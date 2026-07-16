from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration comes from the environment (.env.example documents it)."""

    database_url: str = "postgresql+asyncpg://voxdesk:voxdesk@localhost:5432/voxdesk"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    jwt_secret: str = "change-me-in-production-min-32-bytes!"
    jwt_expires_min: int = 1440
    cors_origins: str = "http://localhost:3000"

    # Provider selection — every external dependency is swappable here.
    llm_provider: str = "mock"
    stt_provider: str = "mock"
    tts_provider: str = "mock"
    embedding_provider: str = "mock"
    telephony_provider: str = "mock"
    voice_engine: str = "mock"
    calendar_provider: str = "mock"
    crm_provider: str = "mock"
    storage_provider: str = "local"

    # Credentials — placeholders until production configuration.
    telnyx_api_key: str = "placeholder"
    telnyx_public_key: str = "placeholder"
    telnyx_connection_id: str = "placeholder"
    dograh_url: str = "http://localhost:8010"
    dograh_api_key: str = "placeholder"
    qwen_api_base: str = "http://localhost:8020/v1"
    qwen_api_key: str = "placeholder"
    whisper_url: str = "http://localhost:8030"
    kokoro_url: str = "http://localhost:8040"
    storage_dir: str = "./storage"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
