from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "InterviewOS AI"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://interviewos:interviewos@localhost:5432/interviewos"
    database_sync_url: str = "postgresql://interviewos:interviewos@localhost:5432/interviewos"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    authentication_secret: str = "change-me-to-a-long-random-secret"
    access_token_expire_minutes: int = 1440
    auth_required: bool = False

    llm_api_key: str = Field(default="", validation_alias=AliasChoices("LLM_API_KEY", "OPENROUTER_API_KEY"))
    llm_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("LLM_MODEL", "OPENROUTER_MODEL"),
    )
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "OPENROUTER_BASE_URL"),
    )
    llm_timeout_seconds: float = Field(
        default=45,
        validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "OPENROUTER_TIMEOUT_SECONDS"),
    )
    llm_max_retries: int = Field(
        default=3,
        validation_alias=AliasChoices("LLM_MAX_RETRIES", "OPENROUTER_MAX_RETRIES"),
    )
    llm_max_output_tokens: int = Field(
        default=2048,
        validation_alias=AliasChoices("LLM_MAX_OUTPUT_TOKENS", "OPENROUTER_MAX_OUTPUT_TOKENS"),
    )
    llm_http_referer: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_HTTP_REFERER", "OPENROUTER_SITE_URL"),
    )
    llm_app_name: str = Field(
        default="InterviewOS AI",
        validation_alias=AliasChoices("LLM_APP_NAME", "OPENROUTER_APP_NAME"),
    )
    session_max_llm_calls: int = 20
    session_max_tokens: int = 80_000

    embedding_model: str = "hashing-fallback"
    vector_store_path: str = "./data/vector_store"
    use_faiss: bool = False

    upload_limit_mb: int = 8
    upload_dir: str = "./uploads"
    media_retention_days: int = 14
    media_storage_enabled: bool = False

    visual_analysis_enabled: bool = True
    visual_frame_sample_hz: float = 2.0
    visual_max_width: int = 640

    tts_voice: str = "en-IN-NeerjaNeural"
    tts_rate: str = "-8%"
    tts_pitch: str = "-3Hz"

    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120

    @field_validator("authentication_secret")
    @classmethod
    def secret_must_exist(cls, value: str) -> str:
        if not value:
            raise ValueError("AUTHENTICATION_SECRET must be set")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        if self.app_env != "production":
            for extra in (
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3010",
                "http://127.0.0.1:3010",
                "http://localhost:3020",
                "http://127.0.0.1:3020",
            ):
                if extra not in origins:
                    origins.append(extra)
        return origins

    @property
    def upload_limit_bytes(self) -> int:
        return self.upload_limit_mb * 1024 * 1024

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key.strip() and self.llm_base_url.strip() and self.llm_model.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
