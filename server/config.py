from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = ""
    JWT_ACCESS_SECRET_KEY: str = ""
    JWT_REFRESH_SECRET_KEY: str = ""
    # 사용자가 최초 아이디 생성시 사용할 이메일과 패스워드
    INITIAL_CONSOLE_USER_EMAIL: str = ""
    INITIAL_CONSOLE_USER_PASSWORD: str = ""

    class Config:
        env_file = ".local.env", ".prod.env"
        env_file_encoding = 'utf-8'


settings = Settings()
