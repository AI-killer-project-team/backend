from pydantic import BaseModel, Field
from app.core.config import settings


class QuestionOut(BaseModel):
    question_id: str
    text: str
    time_limit_seconds: int = Field(default_factory=lambda: settings.time_limit_seconds)


class QuestionNextRequest(BaseModel):
    session_id: str


class AnswerSubmitRequest(BaseModel):
    session_id: str
    question_id: str
    answer_seconds: float
