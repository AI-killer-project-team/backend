from typing import List

from app.schemas.report import ReportResponse, ReportSummary, AnswerTime
from app.utils.stats import average, std_dev


def build_report(session) -> ReportResponse:
    answer_items = [
        AnswerTime(question_id=qid, answer_seconds=sec)
        for qid, sec in session.answers.items()
    ]
    times: List[float] = [item.answer_seconds for item in answer_items]

    if times:
        avg = average(times)
        mn = min(times)
        mx = max(times)
        sd = std_dev(times)
    else:
        avg = mn = mx = sd = 0.0

    summary = ReportSummary(
        average_seconds=avg,
        min_seconds=mn,
        max_seconds=mx,
        std_dev_seconds=sd,
    )

    return ReportResponse(
        session_id=session.session_id,
        total_questions=len(session.questions),
        answered_questions=len(times),
        summary=summary,
        answers=answer_items,
    )
