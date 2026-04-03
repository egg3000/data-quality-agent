import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

VALID_CATEGORIES = [
    "completeness", "validity", "consistency", "uniqueness",
    "referential_integrity", "timeliness", "orphans", "business_rules",
]


class RuleCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: str = Field(..., description="One of: " + ", ".join(VALID_CATEGORIES))
    severity: int = Field(..., ge=1, le=4)
    sql_query: str
    is_active: bool = True
    created_by: Optional[str] = None


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[int] = Field(None, ge=1, le=4)
    sql_query: Optional[str] = None
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    category: str
    severity: int
    sql_query: str
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
