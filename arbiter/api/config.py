from pydantic import BaseSettings

from arbiter.command.main import read_config

config = read_config()

class Settings(BaseSettings):
    APP_ENV: str = config.get('project', 'app_env') if config is not None else 'local'
    JWT_ACCESS_SECRET_KEY: str = config.get('project', 'access_token_key') if config is not None else 'access'
    JWT_REFRESH_SECRET_KEY: str = config.get('project', 'refresh_token_key') if config is not None else 'refresh'
    RDB_CONNECTION_URL: str = config.get('database', 'url') if config is not None else 'postgresql+asyncpg://arbiter:arbiter@localhost:5432/arbiter'
    GAME_TESTER_DEVELOPER_TOKEN: str = config.get('gametester', 'developer_token') if config is not None else 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZDEiOiI2MzlhYmY4ODhjM2QyYzJjNjI1YmJiODYiLCJpZDIiOiI2NTM3MWI4MTM1NTdjZDQzODgzNWI0ZmIifQ.TXDzTOvbVHvOO-I2AoUEzL07Me5VrRKPfrc3dlLL85s'
    GAME_TESTER_PLAY_TIME: int = config.getint('gametester', 'playtime_minute') if config is not None else 30

settings = Settings()
