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
    RDB_CONNECTION_URL: str = "postgresql+asyncpg://fourbarracks:fourbarracks231019!#@dusty-island.cb8f1s4z1aqb.us-west-1.rds.amazonaws.com:5432/dusty_island"
    TEST_RDB_CONNECTION_URL: str = "sqlite+aiosqlite:///arbiter_test.db"
    GAME_TESTER_DEVELOPER_TOKEN: str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZDEiOiI2MzlhYmY4ODhjM2QyYzJjNjI1YmJiODYiLCJpZDIiOiI2NTM3MWI4MTM1NTdjZDQzODgzNWI0ZmIifQ.TXDzTOvbVHvOO-I2AoUEzL07Me5VrRKPfrc3dlLL85s"
    GAME_TESTER_PLAY_TIME: int = 1000 * 60 * 1

    class Config:
        env_file = f"{path}/.env",
        env_file_encoding = 'utf-8'


settings = Settings()
