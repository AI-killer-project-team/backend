from fastapi import APIRouter, HTTPException, UploadFile, File
from app.schemas.session import SessionStartRequest, SessionStartResponse, SessionEndRequest, DocParseResponse
from app.schemas.question import QuestionOut
from app.core.session_store import session_store
from app.services.question_generator import generate_questions
from app.services.company_data import load_company, find_job
from app.core.config import settings
from app.services.doc_parser import extract_text_from_upload

router = APIRouter()


@router.post("/start", response_model=SessionStartResponse)
def start_session(payload: SessionStartRequest):
    if payload.question_count is not None:
        if payload.question_count < 1 or payload.question_count > 10:
            raise HTTPException(status_code=400, detail="question_count must be between 1 and 10")

    company = load_company(payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    job = find_job(company, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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
        voice=payload.voice,
        style=payload.style,
        tts_instructions=payload.tts_instructions,
        tts_speed=payload.tts_speed,
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


@router.post("/parse-doc", response_model=DocParseResponse)
async def parse_doc(file: UploadFile = File(...)):
    file.file.seek(0)
    text = extract_text_from_upload(file.file, file.filename)
    return DocParseResponse(text=text)
