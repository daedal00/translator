from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    secret_key: str
    database_url: str = "sqlite+aiosqlite:///./translator.db"

    whisper_model: str = "medium"
    whisper_device: str = "cuda"

    nllb_model: str = "facebook/nllb-200-distilled-600M"
    nllb_device: str = "cuda"

    bible_api_key: str = ""
    frontend_origin: str = "http://localhost:3000"

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


settings = Settings()
