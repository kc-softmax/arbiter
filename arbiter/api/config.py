import os
from pydantic import BaseSettings

path = os.path.abspath(os.path.dirname(__file__))


class Settings(BaseSettings):
    APP_ENV: str = ""
    JWT_ACCESS_SECRET_KEY: str = ""
    JWT_REFRESH_SECRET_KEY: str = ""
    INITIAL_CONSOLE_USER_EMAIL: str = ""
    INITIAL_CONSOLE_USER_PASSWORD: str = ""
    INITIAL_CONSOLE_USERNAME: str = ""
    RDB_CONNECTION_URL: str = ""
    TEST_RDB_CONNECTION_URL: str = ""

    class Config:
        env_file = path + "/.local.env", path + "/.prod.env"
        env_file_encoding = 'utf-8'


settings = Settings()
