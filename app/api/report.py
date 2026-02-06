from fastapi import APIRouter, HTTPException
from app.schemas.report import ReportResponse
from app.core.session_store import session_store
from app.services.report_builder import build_report

router = APIRouter()


@router.get("/{session_id}", response_model=ReportResponse)
def get_report(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    report = build_report(session)
    return report
