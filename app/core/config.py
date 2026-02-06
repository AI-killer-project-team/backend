from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    default_question_count: int = 5
    time_limit_seconds: int = 120
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.4
    openai_max_output_tokens: int = 512
    openai_stt_model: str = "gpt-4o-mini-transcribe"
    openai_eval_model: Optional[str] = None
    openai_tts_model: str = "gpt-4o-mini-tts"
    tts_default_voice: str = "alloy"
    tts_default_speed: float = 1.0

    class Config:
        env_file = ".env"


settings = Settings()
