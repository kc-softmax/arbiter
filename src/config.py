from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = ""
    JWT_SECRET_KEY: str = ""
    JWT_REFRESH_SECRET_KEY: str = ""

    class Config:
        env_file = ".local.env", ".prod.env"
        env_file_encoding = 'utf-8'


settings = Settings()
