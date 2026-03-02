from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Health Archive"
    DEBUG: bool = False
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-STRONG-RANDOM-KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database (PostgreSQL — обязательно в РФ-контуре)
    DATABASE_URL: str = "postgresql://healthsafe:healthsafe@db:5432/healthsafe"

    # Redis (Celery broker)
    REDIS_URL: str = "redis://redis:6379/0"

    # S3 (Yandex Object Storage / Selectel)
    S3_ENDPOINT_URL: str = "https://storage.yandexcloud.net"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "healthsafe-docs"
    S3_ENCRYPTION_KEY: str = ""  # AES-256 key (base64)

    # Yandex Vision OCR
    YANDEX_VISION_API_KEY: str = ""
    YANDEX_FOLDER_ID: str = ""

    # OpenAI (только анонимизированный текст!)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Email IMAP sync
    IMAP_HOST: str = ""
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""

    # Push notifications (VAPID)
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = "admin@healthsafe.ru"

    # Redactor Service (изолированный шлюз ПДн)
    REDACTOR_URL: str = "http://redactor:8001"          # docker hostname
    REDACTOR_API_KEY: str = "r3d4ct0r-s3cr3t-k3y-ch4ng3-in-pr0duct10n"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://healthsafe.ru"]

    class Config:
        env_file = ".env"


settings = Settings()
