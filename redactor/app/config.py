from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ключ доступа к Redactor — только у владельца инфраструктуры
    REDACTOR_API_KEY: str = "CHANGE-ME-STRONG-RANDOM-KEY"

    # Yandex Vision OCR
    YANDEX_VISION_API_KEY: str = ""
    YANDEX_FOLDER_ID: str = ""

    # Безопасность: никаких логов с содержимым файлов
    LOG_CONTENT: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
