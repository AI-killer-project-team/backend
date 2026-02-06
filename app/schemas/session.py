from typing import Optional
from pydantic import BaseModel
from app.schemas.question import QuestionOut


class SessionStartRequest(BaseModel):
    company_id: str
    job_id: str
    resume_text: Optional[str] = None
    self_intro_text: Optional[str] = None
    jd_text: Optional[str] = None
    question_count: Optional[int] = None


class SessionStartResponse(BaseModel):
    session_id: str
    total_questions: int
    question: QuestionOut


class SessionEndRequest(BaseModel):
    session_id: str
