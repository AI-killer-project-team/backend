import json
import uuid
from typing import List, Optional

from app.core.config import settings
from app.services.company_data import load_company


def _next_id() -> str:
    return uuid.uuid4().hex


def _clip(text: Optional[str], limit: int = 2000) -> Optional[str]:
    if not text:
        return text
    return text[:limit]


def _parse_questions(text: str) -> List[str]:
    try:
        data = json.loads(text)
    except Exception:
        return []

    if isinstance(data, list):
        return [str(item).strip() for item in data if str(item).strip()]

    if isinstance(data, dict):
        items = data.get("questions") or data.get("items") or []
        if isinstance(items, list):
            return [str(item).strip() for item in items if str(item).strip()]

    return []


def _generate_questions_rule_based(
    company_id: str,
    job_id: str,
    resume_text: Optional[str],
    self_intro_text: Optional[str],
    jd_text: Optional[str],
    count: int,
    style: Optional[str],
) -> List[dict]:
    company = load_company(company_id)
    job = None
    for item in company.get("jobs", []):
        if item.get("job_id") == job_id:
            job = item
            break

    questions: List[str] = []

    company_name = company.get("name", "회사")
    job_title = job.get("title", "직무") if job else "직무"

    # Q1 is always a self-introduction
    if style == "pressure":
        questions.append("자기소개를 1분 내로 핵심만 말해 주세요.")
    elif style == "friendly":
        questions.append("편하게 자기소개 부탁드립니다.")
    else:
        questions.append("간단히 자기소개 해주세요.")

    if style == "pressure":
        questions.append(f"{company_name} {job_title}에 지원한 이유를 핵심만 말해 주세요.")
    elif style == "friendly":
        questions.append(f"{company_name} {job_title}에 지원한 이유를 편하게 말씀해 주세요.")
    else:
        questions.append(f"{company_name} {job_title}에 지원한 이유를 말씀해 주세요.")

    if resume_text or self_intro_text:
        if style == "pressure":
            questions.append("이력서/자소서에서 강점이 드러나는 경험 하나를 핵심만 설명해 주세요.")
        elif style == "friendly":
            questions.append("이력서/자소서에서 강점이 드러나는 경험 하나를 편하게 설명해 주세요.")
        else:
            questions.append("이력서/자소서에서 가장 강점을 보여주는 경험 하나를 설명해 주세요.")

    if jd_text:
        if style == "pressure":
            questions.append("채용 공고 요구사항 중 가장 잘 맞는 부분을 근거와 함께 짧게 말해 주세요.")
        elif style == "friendly":
            questions.append("채용 공고 요구사항 중 가장 잘 맞는 부분과 이유를 편하게 말씀해 주세요.")
        else:
            questions.append("채용 공고 요구사항 중 가장 잘 맞는 부분과 이유를 말씀해 주세요.")

    focus_points = job.get("focus_points", []) if job else []
    for point in focus_points:
        if style == "pressure":
            questions.append(f"{point} 관련 경험을 핵심만 말해 주세요.")
        elif style == "friendly":
            questions.append(f"{point}과 관련된 경험을 편하게 설명해 주세요.")
        else:
            questions.append(f"{point}과 관련된 경험을 구체적으로 설명해 주세요.")

    while len(questions) < count:
        if style == "pressure":
            questions.append("가장 어려웠던 상황과 해결 과정을 핵심만 말해 주세요.")
        elif style == "friendly":
            questions.append("가장 어려웠던 상황과 해결 과정을 편하게 설명해 주세요.")
        else:
            questions.append("가장 어려웠던 상황과 해결 과정을 설명해 주세요.")

    questions = questions[:count]

    return [
        {
            "question_id": _next_id(),
            "text": text,
            "time_limit_seconds": settings.time_limit_seconds,
        }
        for text in questions
    ]


def _generate_questions_llm(
    company_id: str,
    job_id: str,
    resume_text: Optional[str],
    self_intro_text: Optional[str],
    jd_text: Optional[str],
    count: int,
    style: Optional[str],
) -> List[dict]:
    from openai import OpenAI

    company = load_company(company_id)
    job = None
    for item in company.get("jobs", []):
        if item.get("job_id") == job_id:
            job = item
            break

    company_name = company.get("name", "회사")
    job_title = job.get("title", "직무") if job else "직무"
    focus_points = job.get("focus_points", []) if job else []

    prompt = {
        "company": {
            "name": company_name,
            "summary": company.get("company_summary"),
            "talent_profile": company.get("talent_profile"),
            "culture_fit": company.get("culture_fit"),
        },
        "job": {
            "id": job_id,
            "title": job_title,
            "focus_points": focus_points,
        },
        "interview_style": style or "neutral",
        "candidate": {
            "resume_text": _clip(resume_text),
            "self_intro_text": _clip(self_intro_text),
        },
        "job_description": _clip(jd_text),
        "constraints": {
            "language": "ko",
            "question_count": count,
            "first_question_fixed": "자기소개 질문(스타일에 맞게 말투만 변경 가능)",
            "output_format": "JSON array of strings",
        },
    }

    system_text = (
        "You are an interview question generator. "
        "Generate concise, realistic interview questions in Korean. "
        "Adjust the wording to match the interview_style (friendly/pressure/neutral). "
        "Return ONLY a JSON array of strings. "
        "The first question must be a self-introduction question in the same style."
    )

    user_text = (
        "Use the following context to generate questions. "
        "Ensure the questions fit the company and role, and avoid duplicates.\n"
        f"Context: {json.dumps(prompt, ensure_ascii=False)}"
    )

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        temperature=settings.openai_temperature,
        max_output_tokens=settings.openai_max_output_tokens,
    )

    text = None
    if hasattr(response, "output_text"):
        text = response.output_text
    if not text and getattr(response, "output", None):
        try:
            text = response.output[0].content[0].text
        except Exception:
            text = None

    questions = _parse_questions(text or "")

    if not questions or "자기소개" not in questions[0]:
        if style == "pressure":
            first = "자기소개를 1분 내로 핵심만 말해 주세요."
        elif style == "friendly":
            first = "편하게 자기소개 부탁드립니다."
        else:
            first = "간단히 자기소개 해주세요."
        questions = [first] + [q for q in questions if q]

    while len(questions) < count:
        if style == "pressure":
            questions.append("가장 어려웠던 상황과 해결 과정을 핵심만 말해 주세요.")
        elif style == "friendly":
            questions.append("가장 어려웠던 상황과 해결 과정을 편하게 설명해 주세요.")
        else:
            questions.append("가장 어려웠던 상황과 해결 과정을 설명해 주세요.")

    questions = questions[:count]

    return [
        {
            "question_id": _next_id(),
            "text": text,
            "time_limit_seconds": settings.time_limit_seconds,
        }
        for text in questions
    ]


def generate_questions(
    company_id: str,
    job_id: str,
    resume_text: Optional[str],
    self_intro_text: Optional[str],
    jd_text: Optional[str],
    count: int,
    style: Optional[str] = None,
) -> List[dict]:
    count = max(1, count)

    if settings.openai_api_key:
        try:
            return _generate_questions_llm(
                company_id=company_id,
                job_id=job_id,
                resume_text=resume_text,
                self_intro_text=self_intro_text,
                jd_text=jd_text,
                count=count,
                style=style,
            )
        except Exception:
            pass

    return _generate_questions_rule_based(
        company_id=company_id,
        job_id=job_id,
        resume_text=resume_text,
        self_intro_text=self_intro_text,
        jd_text=jd_text,
        count=count,
        style=style,
    )
