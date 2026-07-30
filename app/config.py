"""
AegisAI configuration — loads all settings from environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://aegis:aegis@db:5432/aegisai"

    # LLM API keys (optional at startup, required when detection routes are added)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # App
    APP_NAME: str = "AegisAI"
    DEBUG: bool = False


settings = Settings()
