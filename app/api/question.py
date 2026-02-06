from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.schemas.question import QuestionNextRequest, QuestionOut, AnswerSubmitRequest, AnswerAudioResponse
from app.core.session_store import session_store
from app.services.timing_analyzer import record_answer_time
from app.core.config import settings

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
    question_ids = {q["question_id"] for q in session.questions}
    if payload.question_id not in question_ids:
        raise HTTPException(status_code=404, detail="Question not found")
    if payload.answer_seconds < 0 or payload.answer_seconds > settings.time_limit_seconds:
        raise HTTPException(status_code=400, detail="answer_seconds out of range")

    record_answer_time(
        session_id=payload.session_id,
        question_id=payload.question_id,
        answer_seconds=payload.answer_seconds,
    )
    return {"status": "ok"}


@router.post("/answer-audio", response_model=AnswerAudioResponse)
async def submit_answer_audio(
    session_id: str = Form(...),
    question_id: str = Form(...),
    answer_seconds: float = Form(...),
    audio: UploadFile = File(...),
):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    question_ids = {q["question_id"] for q in session.questions}
    if question_id not in question_ids:
        raise HTTPException(status_code=404, detail="Question not found")
    if answer_seconds < 0 or answer_seconds > settings.time_limit_seconds:
        raise HTTPException(status_code=400, detail="answer_seconds out of range")

    transcript = None
    if settings.openai_api_key:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        audio.file.seek(0)
        try:
            result = client.audio.transcriptions.create(
                model=settings.openai_stt_model,
                file=audio.file,
                response_format="text",
            )
            transcript = str(result).strip() if result else None
        except Exception:
            transcript = None

    if transcript:
        transcript = transcript.strip()
    word_count = len(transcript.split()) if transcript else 0
    wpm = (word_count / (answer_seconds / 60)) if answer_seconds > 0 else 0.0

    session_store.record_answer_for_session(
        session_id=session_id,
        question_id=question_id,
        answer_seconds=answer_seconds,
        transcript=transcript,
        word_count=word_count,
        words_per_min=wpm,
    )

    return AnswerAudioResponse(
        session_id=session_id,
        question_id=question_id,
        transcript=transcript,
        answer_seconds=answer_seconds,
        words_per_min=wpm,
    )
