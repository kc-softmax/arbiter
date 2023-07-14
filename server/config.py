from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = ""
    JWT_ACCESS_SECRET_KEY: str = ""
    JWT_REFRESH_SECRET_KEY: str = ""
    INITIAL_CONSOLE_USER_EMAIL: str = ""
    INITIAL_CONSOLE_USER_PASSWORD: str = ""
    RDB_CONNECTION_URL: str = "sqlite+aiosqlite:///arbiter_test.db"

    class Config:
        env_file = "server/.local.env", "server/.prod.env"
        env_file_encoding = 'utf-8'


settings = Settings()
