import json
import uuid
import re
from pathlib import Path
from typing import List, Optional

from app.core.config import settings
from app.services.company_data import load_company

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "companies.json"
_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
_LOG_FILE = _LOG_DIR / "questions.log"


def _load_company(company_id: str) -> dict:
    if not _DATA_PATH.exists():
        return {}
    data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    if data.get("company_id") == company_id:
        return data
    return {}


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


def _log_text(label: str, text: Optional[str]) -> None:
    if not text:
        return
    safe = text.replace("\n", " ").strip()
    if len(safe) > 500:
        safe = safe[:500] + "..."
    print(f"[question_generator] {label}={safe}")
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        _LOG_FILE.open("a", encoding="utf-8").write(f"[question_generator] {label}={safe}\n")
    except Exception:
        pass


def _normalize_question(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "", text)
    return text


def _is_similar(a: str, b: str, threshold: float = 0.85) -> bool:
    from difflib import SequenceMatcher

    na = _normalize_question(a)
    nb = _normalize_question(b)
    if not na or not nb:
        return False
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def _dedupe_similar(questions: List[str], threshold: float = 0.85) -> List[str]:
    result: List[str] = []
    for q in questions:
        if not q or not q.strip():
            continue
        if any(_is_similar(q, exist, threshold) for exist in result):
            continue
        result.append(q)
    return result


def _append_unique(base: List[str], candidates: List[str], threshold: float = 0.85) -> List[str]:
    result = base[:]
    for c in candidates:
        if any(_is_similar(c, exist, threshold) for exist in result):
            continue
        result.append(c)
    return result


def _extract_highlights(text: Optional[str], limit: int = 6) -> List[str]:
    if not text:
        return []
    keywords = [
        "프로젝트",
        "서비스",
        "개발",
        "개선",
        "성과",
        "지표",
        "매출",
        "사용자",
        "트래픽",
        "속도",
        "성능",
        "리팩터링",
        "배포",
        "테스트",
        "운영",
        "자동화",
        "리딩",
        "협업",
        "문제",
        "해결",
        "기술",
        "React",
        "TypeScript",
        "JavaScript",
        "Next",
        "Vue",
        "Node",
        "API",
        "DB",
        "SQL",
    ]
    sentences = re.split(r"[.\n!?]+", text)
    candidates: List[str] = []
    for raw in sentences:
        s = raw.strip()
        if len(s) < 15 or len(s) > 160:
            continue
        if any(ch.isdigit() for ch in s) or any(k.lower() in s.lower() for k in keywords):
            candidates.append(s)
    # fallback: take non-empty lines
    if not candidates:
        candidates = [line.strip() for line in text.splitlines() if 15 <= len(line.strip()) <= 160]
    return candidates[:limit]


def _sanitize_tone(questions: List[str], style: Optional[str]) -> List[str]:
    if style != "pressure":
        return questions
    replacements = {
        "편하게": "핵심만",
        "편안하게": "핵심만",
        "부담 없이": "간단히",
        "자유롭게": "간단히",
        "천천히": "간단히",
        "말씀해 주세요": "말해 주세요",
        "부탁드립니다": "말해 주세요",
    }
    cleaned: List[str] = []
    for q in questions:
        out = q
        for src, dst in replacements.items():
            out = out.replace(src, dst)
        cleaned.append(out)
    return cleaned


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
        highlights = _extract_highlights(f"{resume_text or ''}\n{self_intro_text or ''}")
        for h in highlights[:2]:
            snippet = h[:60]
            if style == "pressure":
                questions.append(f"지원서에 '{snippet}'라고 적었습니다. 본인 역할과 성과를 핵심만 말해 주세요.")
            elif style == "friendly":
                questions.append(f"지원서에 '{snippet}'라고 적은 내용을 조금 더 자세히 설명해 주세요.")
            else:
                questions.append(f"지원서에 '{snippet}'라고 적은 부분에서 본인 역할과 결과를 구체적으로 설명해 주세요.")

        if style == "pressure":
            questions.append("이력서/자소서에서 강점이 드러나는 경험 하나를 핵심만 설명해 주세요.")
        elif style == "friendly":
            questions.append("이력서/자소서에서 강점이 드러나는 경험 하나를 편하게 설명해 주세요.")
        else:
            questions.append("이력서/자소서에서 가장 강점을 보여주는 경험 하나를 설명해 주세요.")

    if jd_text:
        jd_highlights = _extract_highlights(jd_text, limit=3)
        for h in jd_highlights[:1]:
            snippet = h[:60]
            if style == "pressure":
                questions.append(f"공고에 '{snippet}'가 있습니다. 관련 경험을 증거와 함께 말해 주세요.")
            elif style == "friendly":
                questions.append(f"공고에 '{snippet}'가 있는데, 관련 경험이 있다면 편하게 설명해 주세요.")
            else:
                questions.append(f"공고에 '{snippet}'가 있는데, 해당 요구사항과 연결되는 경험을 설명해 주세요.")

        if style == "pressure":
            questions.append("채용 공고 요구사항 중 가장 잘 맞는 부분을 근거와 함께 짧게 말해 주세요.")
        elif style == "friendly":
            questions.append("채용 공고 요구사항 중 가장 잘 맞는 부분과 이유를 편하게 말씀해 주세요.")
        else:
            questions.append("채용 공고 요구사항 중 가장 잘 맞는 부분과 이유를 말씀해 주세요.")

    focus_points = job.get("focus_points", []) if job else []
    if focus_points:
        focus_points = focus_points[:]
        import random
        random.shuffle(focus_points)
    for point in focus_points:
        if style == "pressure":
            questions.append(f"{point} 관련 경험을 핵심만 말해 주세요.")
        elif style == "friendly":
            questions.append(f"{point}과 관련된 경험을 편하게 설명해 주세요.")
        else:
            questions.append(f"{point}과 관련된 경험을 구체적으로 설명해 주세요.")

    if style == "pressure":
        questions.append("성과를 근거와 수치로 설명해 주세요.")
        questions.append("그 판단의 리스크는 무엇이었나요?")

    while len(questions) < count:
        if style == "pressure":
            questions.append("가장 어려웠던 상황과 해결 과정을 핵심만 말해 주세요.")
        elif style == "friendly":
            questions.append("가장 어려웠던 상황과 해결 과정을 편하게 설명해 주세요.")
        else:
            questions.append("가장 어려웠던 상황과 해결 과정을 설명해 주세요.")

    questions = _dedupe_similar(questions)

    if len(questions) < count:
        fallback = [
            "팀에서 의견 충돌이 있었을 때 어떻게 조율했나요?",
            "최근 개선한 기능이나 프로세스를 설명해 주세요.",
            "가장 큰 실수에서 무엇을 배웠나요?",
            "업무 우선순위를 어떻게 정하나요?",
        ]
        questions = _append_unique(questions, fallback)

    questions = questions[:count]
    questions = _sanitize_tone(questions, style)

    result = [
        {
            "question_id": _next_id(),
            "text": text,
            "time_limit_seconds": settings.time_limit_seconds,
        }
        for text in questions
    ]
    print("[question_generator] questions=", [q["text"] for q in result])
    return result


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
    resume_highlights = _extract_highlights(f"{resume_text or ''}\n{self_intro_text or ''}")
    jd_highlights = _extract_highlights(jd_text, limit=3)

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
        "candidate_highlights": resume_highlights,
        "jd_highlights": jd_highlights,
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
            "max_sentence": 2,
            "max_characters": 100,
            "forbidden_topics": [
                "정치",
                "종교",
                "가족/출신",
                "건강/질병",
                "나이/성별",
                "혼인/임신",
                "국적/인종"
            ],
        },
        "style_guidance": {
            "pressure": [
                "Use a direct and strict tone. Do not use friendly phrases like '편하게', '부담 없이', '자유롭게'.",
                "Include at least one question asking for evidence or metrics.",
                "Include at least one question probing risks or trade-offs."
            ]
        },
        "quality_rules": [
            "Avoid repeating similar questions.",
            "Use resume/self_intro content to create at least two personalized questions.",
            "If resume/self_intro is empty, skip personalization."
        ],
    }

    system_text = (
        "당신은 면접 질문을 생성하는 코치입니다. "
        "목표는 '지원자의 자소서/이력서에서 궁금한 점을 파고드는 질문'을 만드는 것입니다. "
        "회사/직무/인재상/컬처핏/직무 포인트를 반영하세요. "
        "interview_style에 맞게 문장 톤을 조정하세요 (friendly/pressure/neutral). "
        "pressure 스타일일 때는 친절한 표현(편하게, 부담 없이, 자유롭게 등)을 사용하지 마세요. "
        "모든 질문은 1~2문장, 100자 이내로 작성하세요. "
        "민감/차별 가능 주제(정치, 종교, 가족/출신, 건강/질병, 나이/성별, 혼인/임신, 국적/인종)는 제외하세요. "
        "candidate_highlights 또는 resume_text/self_intro_text가 있으면 반드시 그 내용에서 2개 이상 개인화 질문을 만드세요. "
        "질문은 일반적인 표현을 피하고, 지원서의 구체적 내용(프로젝트명, 역할, 수치, 기술)을 직접 언급하세요. "
        "질문은 서로 중복되거나 유사하지 않도록 하세요. "
        "출력은 반드시 JSON 문자열 배열만 반환하세요. "
        "첫 질문은 반드시 자기소개 질문이어야 하며, 스타일 톤을 반영하세요."
    )

    user_text = (
        "아래 컨텍스트를 바탕으로 질문을 생성해 주세요. "
        "지원자의 자소서/이력서에서 구체적 성과, 역할, 선택 이유, 문제 해결 방식에 대해 깊게 묻는 질문을 포함하세요. "
        "회사 인재상/컬처핏/직무 포인트와 연결되는 질문을 포함하세요. "
        "중복은 피하세요.\n"
        f"컨텍스트: {json.dumps(prompt, ensure_ascii=False)}"
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
    questions = _dedupe_similar(questions)
    questions = _sanitize_tone(questions, style)
    _log_text("llm_raw", text)
    _log_text("llm_questions", json.dumps(questions, ensure_ascii=False))

    if not questions or "자기소개" not in questions[0]:
        if style == "pressure":
            first = "자기소개를 1분 내로 핵심만 말해 주세요."
        elif style == "friendly":
            first = "편하게 자기소개 부탁드립니다."
        else:
            first = "간단히 자기소개 해주세요."
        questions = [first] + [q for q in questions if q]

    if len(questions) < count:
        fallback = [
            "팀에서 의견 충돌이 있었을 때 어떻게 조율했나요?",
            "최근 개선한 기능이나 프로세스를 설명해 주세요.",
            "가장 큰 실수에서 무엇을 배웠나요?",
            "업무 우선순위를 어떻게 정하나요?",
        ]
        questions = _append_unique(questions, fallback)

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
    print(
        "[question_generator] resume_len=",
        len(resume_text or ""),
        "self_intro_len=",
        len(self_intro_text or ""),
        "jd_len=",
        len(jd_text or ""),
        "style=",
        style,
        "use_llm=",
        bool(settings.openai_api_key),
    )

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
