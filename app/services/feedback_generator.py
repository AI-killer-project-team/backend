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
        "당신은 면접 코치입니다. "
        "후보자의 답변을 평가하고 개선점을 제시합니다. "
        "먼저 해당 질문에 대한 모범 답변(3~5문장)을 작성하세요. "
        "그 다음 답변 품질을 아래 5개 축으로 판단해 가장 약한 축을 한 가지 선택하고, "
        "피드백에서 그 축을 정확히 지적해야 합니다. "
        "평가 축: 관련성(질문과의 직접 연결), 구체성(상황/행동/결과/수치), 근거(경험/사례), 구조(도입-핵심-결론), 기업/직무 맥락 반영. "
        "피드백은 반드시 한 문장으로 작성하며, "
        "형식은 '강점: ...; 개선: ...; 다음 행동: ...'를 유지하세요. "
        "후보자의 답변이 질문과 무관하거나 의미 없는 반복/무성의한 내용이면, "
        "피드백에서 그 사실을 명확히 지적하고 구체화를 요구해야 합니다. "
        "모든 출력은 한국어로 작성합니다. "
        "반환 형식은 JSON 객체이며 키는 'model_answer'와 'feedback'만 허용됩니다. "
        "추가 텍스트, 마크다운, 코드블록 없이 JSON만 반환하세요."
    )

    user_text = (
        "아래 컨텍스트를 참고해 질문과 답변을 평가하세요. "
        "기업/직무 맥락을 반영한 모범 답변을 만들고, "
        "피드백은 한 문장으로 작성하세요. "
        "피드백에는 가장 약한 평가 축을 반드시 포함하고, "
        "즉시 적용 가능한 다음 행동을 제시하세요. "
        "답변이 질문과 무관하거나 내용이 빈약하면 그 사실을 피드백에 명확히 반영하세요.\n"
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


def generate_model_answer(
    company_id: str,
    job_id: str,
    question_text: str,
) -> str:
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
        "constraints": {
            "language": "ko",
            "output_format": "JSON",
            "schema": {
                "model_answer": "string (3-5 sentences, structured and concise)",
            },
        },
    }

    system_text = (
        "당신은 면접 코치입니다. "
        "기업/직무 맥락에 맞는 간결한 모범 답변(3~5문장)을 작성하세요. "
        "모든 출력은 한국어로 작성합니다. "
        "반환 형식은 JSON 객체이며 키는 'model_answer'만 허용됩니다. "
        "추가 텍스트, 마크다운, 코드블록 없이 JSON만 반환하세요."
    )

    user_text = (
        "아래 질문에 대한 모범 답변을 작성하세요. "
        "기업 문화와 직무 포인트를 반영해야 합니다. "
        "출력은 JSON 객체만 허용됩니다.\n"
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
        max_output_tokens=260,
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
    return data.get("model_answer") or ""


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
        "당신은 면접 코치입니다. "
        "후보자의 전체 면접 수행을 정확히 3줄로 요약하세요. "
        "각 줄은 다음을 반드시 다뤄야 합니다: 1) 전반적 강점, 2) 개선점, 3) 다음 면접을 위한 구체적 행동 팁. "
        "출력은 한국어 JSON 배열이어야 하며 문자열만 포함합니다. "
        "추가 텍스트, 마크다운, 코드블록 없이 JSON 배열만 반환하세요."
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
