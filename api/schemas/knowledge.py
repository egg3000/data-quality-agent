import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

VALID_SOURCE_TYPES = ["agent", "analyst", "rule", "conversation"]


class KnowledgeCreate(BaseModel):
    title: str = Field(..., max_length=300)
    content: str
    source_type: str = Field(..., description="One of: " + ", ".join(VALID_SOURCE_TYPES))
    source_id: Optional[uuid.UUID] = None
    tags: Optional[list[str]] = None


class KnowledgeResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    source_type: str
    source_id: Optional[uuid.UUID]
    tags: Optional[list[str]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSearchResult(BaseModel):
    entry: KnowledgeResponse
    similarity: float
