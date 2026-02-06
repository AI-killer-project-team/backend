from typing import Optional
from pydantic import BaseModel


class TtsRequest(BaseModel):
    session_id: str
    question_id: Optional[str] = None
    text: Optional[str] = None
    voice: Optional[str] = None
    instructions: Optional[str] = None
    speed: Optional[float] = None
    response_format: Optional[str] = "mp3"
