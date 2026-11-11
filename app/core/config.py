# app/core/config.py

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):

    # =====================================================
    # DATABASE
    # =====================================================

    database_url: str

    # =====================================================
    # TELEGRAM
    # =====================================================

    telegram_local_bot_token: str

    telegram_cloud_bot_token: str = ""

    telegram_local_api_url: str = (
        "http://127.0.0.1:8081"
    )

    telegram_storage_backend: str = "local"

    # =====================================================
    # PAYSTACK
    # =====================================================

    paystack_secret_key: str

    paystack_public_key: str = ""

    paystack_base_url: str = (
        "https://api.paystack.co"
    )


    # =====================================================
    # STAGING
    # =====================================================

    staging_directory: str = (
        "./storage/staging"
    )

    # =====================================================
    # LEGACY / CHUNKING
    # =====================================================

    max_file_size: int = (
        20 * 1024 * 1024
    )

    telegram_chunk_size: int = (
        19 * 1024 * 1024
    )

    # =====================================================
    # AUTH
    # =====================================================

    jwt_secret_key: str

    jwt_algorithm: str = "HS256"

    jwt_access_token_expire_minutes: int = 60

    # =====================================================
    # FRONTEND
    # =====================================================

    frontend_url: str = (
        "http://localhost:5173"
    )

    # =====================================================
    # EMAIL
    # =====================================================

    email_from: str

    smtp_host: str = "smtp.gmail.com"

    smtp_port: int = 587

    smtp_username: str

    smtp_password: str

    # =====================================================
    # PYDANTIC
    # =====================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
