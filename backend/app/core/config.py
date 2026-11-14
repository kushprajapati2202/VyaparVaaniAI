import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    PROJECT_NAME: str = "VyaparVaani AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "vyaparvaani-ai-secret-key-google-gemini-hackathon-2026"

    # Gemini & Google Cloud
    GEMINI_API_KEY: str = ""
    GEMINI_LIVE_MODEL: str = "gemini-2.0-flash-exp"
    GEMINI_REASONING_MODEL: str = "gemini-2.0-flash"

    # Database: Async SQLite by default for easy, robust local zero-setup dev
    DATABASE_URL: str = "sqlite+aiosqlite:///./vyaparvaani.db"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]

    # Business Rule Thresholds
    MAX_UNAPPROVED_ORDER_AMOUNT: float = 15000.0
    MAX_CREDIT_UTILIZATION_PERCENT: float = 0.85
    MAX_UNAPPROVED_DISCOUNT_PERCENT: float = 0.10

    # Audio Settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024

settings = Settings()
