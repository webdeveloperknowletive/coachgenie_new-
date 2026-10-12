from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


class StartSessionRequest(BaseModel):
    feature: str
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
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_tokens: Optional[int] = None
    model_used: Optional[str] = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str