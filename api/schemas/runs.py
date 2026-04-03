import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RunTrigger(BaseModel):
    rule_id: Optional[uuid.UUID] = None


class RunResponse(BaseModel):
    id: uuid.UUID
    rule_id: uuid.UUID
    rule_name: Optional[str] = None
    triggered_by: str
    status: str
    error_count: int
    started_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RunBatchResponse(BaseModel):
    total_rules: int
    completed: int
    failed: int
    total_errors: int
    runs: list[RunResponse]
