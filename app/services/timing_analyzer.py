from app.core.session_store import session_store


def record_answer_time(session_id: str, question_id: str, answer_seconds: float) -> None:
    session_store.record_answer_for_session(
        session_id=session_id,
        question_id=question_id,
        answer_seconds=answer_seconds,
    )
