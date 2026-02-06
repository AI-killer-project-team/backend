from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid


@dataclass
class AnswerRecord:
    question_id: str
    answer_seconds: float
    transcript: Optional[str] = None
    word_count: int = 0
    words_per_min: float = 0.0
    model_answer: Optional[str] = None
    feedback: Optional[str] = None


@dataclass
class Session:
    session_id: str
    company_id: str
    job_id: str
    resume_text: Optional[str]
    self_intro_text: Optional[str]
    jd_text: Optional[str]
    voice: Optional[str]
    style: Optional[str]
    tts_instructions: Optional[str]
    tts_speed: Optional[float]
    questions: List[dict]
    answers: Dict[str, AnswerRecord] = field(default_factory=dict)
    summary_lines: List[str] = field(default_factory=list)
    current_index: int = 0
    ended: bool = False


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}

    def create_session(
        self,
        company_id: str,
        job_id: str,
        resume_text: Optional[str],
        self_intro_text: Optional[str],
        jd_text: Optional[str],
        voice: Optional[str],
        style: Optional[str],
        tts_instructions: Optional[str],
        tts_speed: Optional[float],
        questions: List[dict],
    ) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            company_id=company_id,
            job_id=job_id,
            resume_text=resume_text,
            self_intro_text=self_intro_text,
            jd_text=jd_text,
            voice=voice,
            style=style,
            tts_instructions=tts_instructions,
            tts_speed=tts_speed,
            questions=questions,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.ended = True

    def get_next_question(self, session_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        if session.current_index >= len(session.questions):
            return None
        question = session.questions[session.current_index]
        session.current_index += 1
        return question

    def record_answer_for_session(
        self,
        session_id: str,
        question_id: str,
        answer_seconds: float,
        transcript: Optional[str] = None,
        word_count: int = 0,
        words_per_min: float = 0.0,
    ) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        session.answers[question_id] = AnswerRecord(
            question_id=question_id,
            answer_seconds=answer_seconds,
            transcript=transcript,
            word_count=word_count,
            words_per_min=words_per_min,
        )


session_store = SessionStore()
