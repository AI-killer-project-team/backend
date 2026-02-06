from typing import List
from pydantic import BaseModel


class AnswerTime(BaseModel):
    question_id: str
    answer_seconds: float


class ReportSummary(BaseModel):
    average_seconds: float
    min_seconds: float
    max_seconds: float
    std_dev_seconds: float


class ReportResponse(BaseModel):
    session_id: str
    total_questions: int
    answered_questions: int
    summary: ReportSummary
    answers: List[AnswerTime]
