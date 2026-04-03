import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    id: uuid.UUID
    rule_id: uuid.UUID
    rule_run_id: uuid.UUID
    rule_name: Optional[str] = None
    error_data: dict
    is_resolved: bool
    detected_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ErrorResolveRequest(BaseModel):
    is_resolved: bool


class ErrorSummaryItem(BaseModel):
    rule_id: uuid.UUID
    rule_name: Optional[str] = None
    summary_date: date
    total_errors: int
    new_errors: int
    resolved_errors: int

    model_config = {"from_attributes": True}
