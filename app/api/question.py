from fastapi import APIRouter, HTTPException
from app.schemas.question import QuestionNextRequest, QuestionOut, AnswerSubmitRequest
from app.core.session_store import session_store
from app.services.timing_analyzer import record_answer_time

router = APIRouter()


@router.post("/next", response_model=QuestionOut)
def next_question(payload: QuestionNextRequest):
    session = session_store.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    question = session_store.get_next_question(payload.session_id)
    if not question:
        raise HTTPException(status_code=404, detail="No more questions")

    return QuestionOut(**question)


@router.post("/answer")
def submit_answer(payload: AnswerSubmitRequest):
    session = session_store.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    record_answer_time(
        session_id=payload.session_id,
        question_id=payload.question_id,
        answer_seconds=payload.answer_seconds,
    )
    return {"status": "ok"}
