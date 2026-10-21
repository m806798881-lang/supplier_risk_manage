from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='UTF-8')

    # JWT
    secret_key: str = "dev-secret-key-CHANGE-ME-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # 数据库
    database_url: str = 'sqlite+aiosqlite:///./supplier.db'


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
