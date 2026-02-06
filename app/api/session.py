from fastapi import APIRouter, HTTPException
from app.schemas.session import SessionStartRequest, SessionStartResponse, SessionEndRequest
from app.schemas.question import QuestionOut
from app.core.session_store import session_store
from app.services.question_generator import generate_questions
from app.core.config import settings

router = APIRouter()


@router.post("/start", response_model=SessionStartResponse)
def start_session(payload: SessionStartRequest):
    questions = generate_questions(
        company_id=payload.company_id,
        job_id=payload.job_id,
        resume_text=payload.resume_text,
        self_intro_text=payload.self_intro_text,
        jd_text=payload.jd_text,
        count=payload.question_count or settings.default_question_count,
    )
    session = session_store.create_session(
        company_id=payload.company_id,
        job_id=payload.job_id,
        resume_text=payload.resume_text,
        self_intro_text=payload.self_intro_text,
        jd_text=payload.jd_text,
        questions=questions,
    )

    first_question = session_store.get_next_question(session.session_id)
    if not first_question:
        raise HTTPException(status_code=500, detail="Failed to generate questions")

    return SessionStartResponse(
        session_id=session.session_id,
        total_questions=len(session.questions),
        question=QuestionOut(**first_question),
    )


@router.post("/end")
def end_session(payload: SessionEndRequest):
    session = session_store.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_store.end_session(payload.session_id)
    return {"status": "ended"}
