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
    GEMINI_API_VERSION: str = "v1beta"
    GEMINI_LIVE_MODEL: str = "gemini-3.8-live"
    # Text model used only by the fallback path (Live API unavailable)
    GEMINI_REASONING_MODEL: str = "gemini-3.5-flash"
    GEMINI_VOICE: str = "Kore"
    # Vertex AI (Cloud Run) — when true, uses ADC + project/location instead of API key
    GOOGLE_GENAI_USE_VERTEXAI: bool = False
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    # Voice activity detection tuning (counter noise)
    VAD_SILENCE_MS: int = 500
    VAD_PREFIX_PADDING_MS: int = 300
    # Cost levers: Live bills the full context (incl. prior audio) on every turn.
    # gemini-3.8-live does not accept thinking_level / thinking_budget (verified), so context size is the lever.
    LIVE_RESET_CONTEXT_AFTER_TXN: bool = True   # fresh context once a transaction is closed; state lives in the toolkit
    LIVE_CONTEXT_TRIGGER_TOKENS: int = 12000
    LIVE_CONTEXT_TARGET_TOKENS: int = 6000

    # Transaction safety
    UNDO_WINDOW_MINUTES: int = 15
    DUPLICATE_WINDOW_SECONDS: int = 120
    LARGE_PAYMENT_WARNING_AMOUNT: float = 25000.0

    # ROI / unit economics assumptions (override per deployment)
    MANUAL_SECONDS_PER_TRANSACTION: float = 95.0   # pen-and-khata + billing software entry
    OPERATOR_COST_PER_HOUR_INR: float = 120.0
    USD_TO_INR: float = 84.0
    # gemini-3.8-live paid-tier USD per 1M tokens (Gemini pricing page, Nov 2026)
    LIVE_PRICE_INPUT_AUDIO_PER_M: float = 3.00
    LIVE_PRICE_INPUT_TEXT_PER_M: float = 0.75
    LIVE_PRICE_OUTPUT_AUDIO_PER_M: float = 12.00
    LIVE_PRICE_OUTPUT_TEXT_PER_M: float = 4.50
    SUBSCRIPTION_PRICE_INR_PER_MONTH: float = 299.0

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
