import os
from pydantic import BaseSettings

path = os.path.abspath(os.path.dirname(__file__))


class Settings(BaseSettings):
    APP_ENV: str = "local"
    JWT_ACCESS_SECRET_KEY: str = "access"
    JWT_REFRESH_SECRET_KEY: str = "refresh"
    INITIAL_CONSOLE_USER_EMAIL: str = "admin@admin.com"
    INITIAL_CONSOLE_USER_PASSWORD: str = "admin"
    INITIAL_CONSOLE_USERNAME: str = "admin"
    RDB_CONNECTION_URL: str = "sqlite+aiosqlite:///arbiter.db"
    TEST_RDB_CONNECTION_URL: str = "sqlite+aiosqlite:///arbiter_test.db"

    class Config:
        env_file = f"{path}/.local.env", f"{path}/.prod.env"
        env_file_encoding = 'utf-8'


settings = Settings()
