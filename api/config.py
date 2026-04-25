"""
Application configuration via pydantic-settings.

All configuration is loaded from environment variables or a .env file.
Secrets should be injected via Google Secret Manager at Cloud Run runtime.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the PromptWars LearnAI API."""

    # ── Google Cloud ──────────────────────────────────────────────
    gcp_project_id: str = "promptwars-494401"
    gcp_region: str = "asia-south1"

    # ── PostgreSQL (Cloud SQL) ────────────────────────────────────
    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_db: str = "promptwars"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        """Async database URL for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis (Memorystore) ───────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_ttl_seconds: int = 300  # 5-minute cache TTL

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # ── Firebase Auth ─────────────────────────────────────────────
    firebase_credentials_base64: str = ""
    firebase_api_key: str = ""

    # ── Vertex AI / Gemini ────────────────────────────────────────
    gemini_model_flash: str = "gemini-1.5-flash-002"
    gemini_model_pro: str = "gemini-1.5-pro-002"
    gemini_embedding_model: str = "text-embedding-004"
    gemini_max_context_tokens: int = 8_000
    gemini_max_output_tokens: int = 1_024
    gemini_temperature: float = 0.4

    # ── Application ───────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"
    api_rate_limit_per_minute: int = 60
    inference_rate_limit_per_minute: int = 10
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
