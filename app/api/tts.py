from io import BytesIO
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.tts import TtsRequest
from app.core.session_store import session_store
from app.core.config import settings

router = APIRouter()


def _resolve_instructions(style: Optional[str], stored: Optional[str], override: Optional[str]) -> Optional[str]:
    if override:
        return override
    if stored:
        return stored
    if style == "pressure":
        return "압박 면접관 톤으로, 간결하고 단호하게 질문하세요."
    if style == "friendly":
        return "친절하고 차분한 면접관 톤으로 질문하세요."
    return None


@router.post("/speak")
def speak(payload: TtsRequest):
    session = session_store.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    text = payload.text
    if not text and payload.question_id:
        question_map = {q["question_id"]: q["text"] for q in session.questions}
        text = question_map.get(payload.question_id)

    if not text:
        raise HTTPException(status_code=400, detail="text or question_id required")

    voice = payload.voice or session.voice or settings.tts_default_voice
    speed = payload.speed or session.tts_speed or settings.tts_default_speed
    instructions = _resolve_instructions(session.style, session.tts_instructions, payload.instructions)

    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not set")

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.audio.speech.create(
        model=settings.openai_tts_model,
        voice=voice,
        input=text,
        response_format=payload.response_format or "mp3",
        speed=speed,
        instructions=instructions,
    )

    audio_bytes = getattr(response, "content", None)
    if audio_bytes is None:
        try:
            audio_bytes = response.read()
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to generate audio")

    media_type = "audio/mpeg" if (payload.response_format or "mp3") == "mp3" else "audio/wav"
    return StreamingResponse(BytesIO(audio_bytes), media_type=media_type)
