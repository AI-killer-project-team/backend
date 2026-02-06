from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    default_question_count: int = 5
    time_limit_seconds: int = 120

    class Config:
        env_file = ".env"


settings = Settings()
