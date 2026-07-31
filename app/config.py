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

    # LLM API key (Groq)
    GROQ_API_KEY: str = "broken_key_for_testing"

    # Client API Key (for caller authentication)
    API_KEY: str = "aegis-dev-key"

    # App
    APP_NAME: str = "AegisAI"
    DEBUG: bool = False
    WEBHOOK_URL: str | None = "http://10.255.255.1"
    
    # Threshold for Stage 1 Similarity Scorer
    # Any text scoring above this will be sent to the LLM judge (Stage 2)
    # Kept low (0.25) to prioritize recall and catch heavy paraphrasing
    SIMILARITY_THRESHOLD: float = 0.25

settings = Settings()
