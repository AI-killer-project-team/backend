from typing import List
import re

from app.schemas.report import ReportResponse, ReportSummary, AnswerTime
from app.utils.stats import average, std_dev
from app.services.feedback_generator import (
    generate_model_answer,
    generate_question_feedback,
    generate_summary_lines,
)
from app.core.config import settings


def build_report(session) -> ReportResponse:
    question_text_map = {q["question_id"]: q["text"] for q in session.questions}
    print(
        "[report_builder]",
        "session_id=",
        session.session_id,
        "total_questions=",
        len(session.questions),
        "answered=",
        len(session.answers),
    )
    ordered_records = [
        session.answers[qid]
        for qid in question_text_map.keys()
        if qid in session.answers
    ]
    answers = ordered_records

    times: List[float] = [a.answer_seconds for a in answers]
    wpm_values: List[float] = [a.words_per_min for a in answers if a.words_per_min > 0]

    if times:
        avg = average(times)
        mn = min(times)
        mx = max(times)
        sd = std_dev(times)
    else:
        avg = mn = mx = sd = 0.0

    average_wpm = average(wpm_values) if wpm_values else 0.0

    def wpm_label(value: float) -> str:
        if value <= 0:
            return "알 수 없음"
        if value < 120:
            return "느림"
        if value <= 170:
            return "적정"
        return "빠름"

    summary = {
        "average_seconds": avg,
        "min_seconds": mn,
        "max_seconds": mx,
        "std_dev_seconds": sd,
        "average_wpm": average_wpm,
        "average_wpm_label": wpm_label(average_wpm),
    }

    def is_unreliable_transcript(text: str) -> bool:
        if not text:
            return True
        stripped = text.strip()
        if len(stripped) < 20:
            return True
        if re.search(r"(.)\1{5,}", stripped):
            return True
        unique_ratio = len(set(stripped)) / max(len(stripped), 1)
        if unique_ratio < 0.2:
            return True
        letters = re.findall(r"[A-Za-z가-힣]", stripped)
        if len(letters) < 10:
            return True
        return False

    reliable_answers = [a for a in answers if not is_unreliable_transcript(a.transcript or "")]

    summary_lines: List[str] = session.summary_lines or []
    if not summary_lines and reliable_answers:
        if settings.openai_api_key:
            try:
                summary_lines = generate_summary_lines(summary, reliable_answers)
                session.summary_lines = summary_lines
            except Exception:
                summary_lines = []

    if not summary_lines:
        summary_lines = [
            "일부 답변이 면접 질문과 무관하거나 내용이 불분명했습니다.",
            "의미 있는 사례, 역할, 결과를 포함해 답변의 정보량을 늘려보세요.",
            "다음 인터뷰에서는 질문 의도를 먼저 정리한 뒤 핵심 근거로 답변해 주세요.",
        ]
        session.summary_lines = summary_lines

    answer_items: List[AnswerTime] = []

    for record in answers:
        question_text = question_text_map.get(record.question_id, "")

        if settings.openai_api_key and not record.model_answer:
            try:
                record.model_answer = generate_model_answer(
                    company_id=session.company_id,
                    job_id=session.job_id,
                    question_text=question_text,
                )
            except Exception:
                pass

        unreliable = is_unreliable_transcript(record.transcript or "")
        if unreliable and not record.feedback:
            record.feedback = "답변 인식이 불충분해 피드백을 생성하지 못했습니다. 조용한 환경에서 다시 답변해 주세요."

        if settings.openai_api_key and record.transcript and not record.feedback and not unreliable:
            try:
                feedback = generate_question_feedback(
                    company_id=session.company_id,
                    job_id=session.job_id,
                    question_text=question_text,
                    transcript=record.transcript,
                )
                record.model_answer = feedback.get("model_answer")
                record.feedback = feedback.get("feedback")
            except Exception:
                pass

        answer_items.append(
            AnswerTime(
                question_id=record.question_id,
                question_text=question_text,
                answer_seconds=record.answer_seconds,
                words_per_min=record.words_per_min,
                wpm_label=wpm_label(record.words_per_min),
                transcript=record.transcript,
                model_answer=record.model_answer,
                feedback=record.feedback,
            )
        )

    return ReportResponse(
        session_id=session.session_id,
        total_questions=len(session.questions),
        answered_questions=len(answers),
        summary=ReportSummary(summary_lines=summary_lines, **summary),
        answers=answer_items,
    )
