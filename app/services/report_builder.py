from typing import List

from app.schemas.report import ReportResponse, ReportSummary, AnswerTime
from app.utils.stats import average, std_dev
from app.services.feedback_generator import generate_question_feedback, generate_summary_lines
from app.core.config import settings


def build_report(session) -> ReportResponse:
    question_text_map = {q["question_id"]: q["text"] for q in session.questions}
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

    summary_lines: List[str] = []
    if settings.openai_api_key and answers and any(a.transcript for a in answers):
        try:
            summary_lines = generate_summary_lines(summary, answers)
        except Exception:
            summary_lines = []

    answer_items: List[AnswerTime] = []

    for record in answers:
        question_text = question_text_map.get(record.question_id, "")

        if settings.openai_api_key and record.transcript and not record.feedback:
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
