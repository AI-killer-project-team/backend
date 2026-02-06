import json
from typing import List

from app.core.config import settings
from app.core.session_store import AnswerRecord
from app.services.company_data import load_company


def _safe_json_loads(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        return {}


def generate_question_feedback(
    company_id: str,
    job_id: str,
    question_text: str,
    transcript: str,
) -> dict:
    from openai import OpenAI

    company = load_company(company_id)
    job = None
    for item in company.get("jobs", []):
        if item.get("job_id") == job_id:
            job = item
            break

    prompt = {
        "company": {
            "name": company.get("name"),
            "summary": company.get("company_summary"),
            "talent_profile": company.get("talent_profile"),
            "culture_fit": company.get("culture_fit"),
        },
        "job": {
            "id": job_id,
            "title": job.get("title") if job else None,
            "focus_points": job.get("focus_points", []) if job else [],
        },
        "question": question_text,
        "answer": transcript,
        "constraints": {
            "language": "ko",
            "output_format": "JSON",
            "schema": {
                "model_answer": "string",
                "feedback": "string (one sentence: good + improve)",
            },
        },
    }

    system_text = (
        "You are an interview coach. "
        "Provide a short model answer structure and a one-sentence feedback. "
        "Return ONLY JSON with keys: model_answer, feedback."
    )

    user_text = f"Context: {json.dumps(prompt, ensure_ascii=False)}"

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_eval_model or settings.openai_model,
        input=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        temperature=0.3,
        max_output_tokens=300,
    )

    text = None
    if hasattr(response, "output_text"):
        text = response.output_text
    if not text and getattr(response, "output", None):
        try:
            text = response.output[0].content[0].text
        except Exception:
            text = None

    data = _safe_json_loads(text or "")
    return {
        "model_answer": data.get("model_answer"),
        "feedback": data.get("feedback"),
    }


def generate_summary_lines(
    summary: dict,
    answers: List[AnswerRecord],
) -> List[str]:
    from openai import OpenAI

    payload = {
        "summary": summary,
        "answers": [
            {
                "question_id": a.question_id,
                "answer_seconds": a.answer_seconds,
                "transcript": a.transcript,
                "words_per_min": a.words_per_min,
            }
            for a in answers
        ],
        "constraints": {
            "language": "ko",
            "lines": 3,
            "format": "JSON array of strings",
        },
    }

    system_text = (
        "You are an interview coach. "
        "Summarize in exactly 3 concise lines. "
        "Return ONLY a JSON array of strings."
    )
    user_text = f"Context: {json.dumps(payload, ensure_ascii=False)}"

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_eval_model or settings.openai_model,
        input=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        temperature=0.3,
        max_output_tokens=200,
    )

    text = None
    if hasattr(response, "output_text"):
        text = response.output_text
    if not text and getattr(response, "output", None):
        try:
            text = response.output[0].content[0].text
        except Exception:
            text = None

    try:
        data = json.loads(text or "")
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    except Exception:
        pass

    return []
