from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid


class StartSessionRequest(BaseModel):
    feature: str  # doubt_solver | career_guidance | ai_tutor | roleplay_career | institute_analytics
    student_id: Optional[uuid.UUID] = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    tokens_used: int
    session_id: str


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    feature: str
    started_at: str
    ended_at: Optional[str] = None
    total_tokens: Optional[int] = None
    model_used: Optional[str] = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str

