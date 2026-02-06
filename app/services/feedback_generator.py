import json
import logging

from typing import List

from app.core.config import settings
from app.core.session_store import AnswerRecord
from app.services.company_data import load_company

logger = logging.getLogger(__name__)

def _safe_json_loads(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {text[:100]}... Error: {e}")
        return {}
    except Exception as e:
        logger.error(f"An unexpected error occured during JSON parsing: {e}")
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
        "You are an expert interview coach. "
        "Your task is to provide constructive feedback for a candidate's interview answer. "
        "First, generate a concise model answer structure (3-5 sentences, focusing on key points). "
        "Second, provide a single, actionable sentence of feedback that highlights one strength and one area for improvement. "
        "All output content in the JSON, specifically the 'model_answer' and 'feedback' values, must be in Korean. "
        "Return ONLY a JSON object with keys: 'model_answer' and 'feedback'."
    )

    user_text = (
        "Analyze the candidate's answer to the following question, considering the company's talent profile and culture fit, "
        "and the job's key focus points. Provide a model answer that aligns with these contexts and feedback that helps the candidate improve.\n"
        f"Context: {json.dumps(prompt, ensure_ascii=False)}"
    )

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
        "You are an expert interview coach. "
        "Summarize the candidate's overall interview performance in exactly three concise lines. "
        "Each line should cover a distinct aspect: 1) overall strengths, 2) key areas for improvement, and 3) one actionable tip for the next interview. "
        "All strings in the output JSON array must be in Korean. "
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
