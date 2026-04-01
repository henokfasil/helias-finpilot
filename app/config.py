from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Telegram (not required for dashboard-only deployments)
    telegram_bot_token: str = Field("", env="TELEGRAM_BOT_TOKEN")

    # OpenAI (not required for dashboard-only deployments)
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL")
    openai_vision_model: str = Field("gpt-4o", env="OPENAI_VISION_MODEL")

    # Gemini — used for image/document extraction (better Amharic support)
    gemini_api_key: str = Field("", env="GEMINI_API_KEY")
    gemini_vision_model: str = Field("gemini-2.0-flash", env="GEMINI_VISION_MODEL")

    # Database
    database_url: str = Field("sqlite:///./finpilot.db", env="DATABASE_URL")

    # App
    app_env: str = Field("development", env="APP_ENV")
    app_log_level: str = Field("INFO", env="APP_LOG_LEVEL")
    upload_dir: str = Field("./uploads", env="UPLOAD_DIR")

    # Company seed defaults
    default_company_name: str = Field("Helias AI and Analytics", env="DEFAULT_COMPANY_NAME")
    default_company_currency: str = Field("ETB", env="DEFAULT_COMPANY_CURRENCY")
    default_admin_telegram_id: str = Field("", env="DEFAULT_ADMIN_TELEGRAM_ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
