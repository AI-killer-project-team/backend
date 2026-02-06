from fastapi import FastAPI
from app.api import session, question, report, tts

app = FastAPI(title="Interview Trainer API")

app.include_router(session.router, prefix="/api/session", tags=["session"])
app.include_router(question.router, prefix="/api/question", tags=["question"])
app.include_router(report.router, prefix="/api/report", tags=["report"])
app.include_router(tts.router, prefix="/api/tts", tags=["tts"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
