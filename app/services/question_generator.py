import json
import uuid
from pathlib import Path
from typing import List, Optional

from app.core.config import settings

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "companies.json"


def _load_company(company_id: str) -> dict:
    if not _DATA_PATH.exists():
        return {}
    data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    if data.get("company_id") == company_id:
        return data
    return {}


def _next_id() -> str:
    return uuid.uuid4().hex


def generate_questions(
    company_id: str,
    job_id: str,
    resume_text: Optional[str],
    self_intro_text: Optional[str],
    jd_text: Optional[str],
    count: int,
) -> List[dict]:
    company = _load_company(company_id)
    job = None
    for item in company.get("jobs", []):
        if item.get("job_id") == job_id:
            job = item
            break

    questions: List[str] = []

    company_name = company.get("name", "the company")
    job_title = job.get("title", "the role") if job else "the role"

    # Q1 is always a self-introduction
    questions.append("Please introduce yourself briefly.")

    questions.append(
        f"Why do you want to join {company_name} as a {job_title}?"
    )

    if resume_text or self_intro_text:
        questions.append(
            "Tell me about a project or experience on your resume that best shows your strengths."
        )

    if jd_text:
        questions.append(
            "Based on the job description, which requirement fits you best and why?"
        )

    focus_points = job.get("focus_points", []) if job else []
    for point in focus_points:
        questions.append(
            f"Can you share an example related to: {point}?"
        )

    # Fill to requested count with generic questions
    while len(questions) < count:
        questions.append("Tell me about a challenging situation and how you handled it.")

    questions = questions[:count]

    return [
        {
            "question_id": _next_id(),
            "text": text,
            "time_limit_seconds": settings.time_limit_seconds,
        }
        for text in questions
    ]
