from pydantic import BaseModel
from typing import Optional, List, Any


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    canvas_data: Optional[Any] = None
    created_at: str


class SessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    last_message_preview: Optional[str] = None


class SessionDetail(BaseModel):
    id: str
    title: str
    messages: List[MessageResponse]
    created_at: str


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"


class UpdateTitleRequest(BaseModel):
    title: str
