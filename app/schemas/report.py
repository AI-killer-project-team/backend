from typing import List, Optional
from pydantic import BaseModel


class AnswerTime(BaseModel):
    question_id: str
    question_text: str
    answer_seconds: float
    words_per_min: float
    transcript: Optional[str] = None
    model_answer: Optional[str] = None
    feedback: Optional[str] = None


class ReportSummary(BaseModel):
    average_seconds: float
    min_seconds: float
    max_seconds: float
    std_dev_seconds: float
    average_wpm: float
    summary_lines: List[str]


class ReportResponse(BaseModel):
    session_id: str
    total_questions: int
    answered_questions: int
    summary: ReportSummary
    answers: List[AnswerTime]
