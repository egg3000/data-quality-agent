import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    response: str


class ConversationResponse(BaseModel):
    id: uuid.UUID
    session_id: str
    analyst_id: Optional[str]
    started_at: datetime
    last_active_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
