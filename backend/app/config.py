"""ZAPRICA Backend Configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "ZAPRICA"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://zaprica:zaprica_dev_password@localhost:5432/zaprica"
    database_url_sync: str = "postgresql://zaprica:zaprica_dev_password@localhost:5432/zaprica"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT Authentication
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "zaprica_minio"
    minio_secret_key: str = "zaprica_minio_secret"
    minio_bucket: str = "zaprica-evidence"
    minio_secure: bool = False

    # LLM Configuration (mock by default for MVP)
    planner_llm_provider: str = "mock"  # "openai", "anthropic", "mock"
    planner_llm_model: str = "gpt-4o"
    planner_llm_api_key: str = ""
    extractor_llm_provider: str = "mock"  # "openai", "anthropic", "ollama", "mock"
    extractor_llm_model: str = "gpt-4o-mini"
    extractor_llm_api_key: str = ""

    # Investigation Limits
    max_investigation_iterations: int = 50
    max_investigation_time_seconds: int = 3600
    max_tool_calls_per_investigation: int = 200
    max_concurrent_investigations: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
