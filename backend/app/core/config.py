"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os


class Settings:
    """Application settings populated from environment variables."""

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:password@localhost:5432/civicpulse",
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    TRIAGE_PROVIDER: str = os.getenv("TRIAGE_PROVIDER", "rules")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    RATE_LIMIT_PER_MIN: int = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))
    STATS_CACHE_TTL: int = int(os.getenv("STATS_CACHE_TTL", "30"))
    TRIAGE_CACHE_TTL: int = int(os.getenv("TRIAGE_CACHE_TTL", "86400"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "10"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
