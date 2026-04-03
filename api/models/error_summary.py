import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, UUIDPrimaryKey


class ErrorSummary(UUIDPrimaryKey, Base):
    __tablename__ = "error_summaries"
    __table_args__ = (
        UniqueConstraint("rule_id", "summary_date", name="uq_rule_summary_date"),
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id"), nullable=False, index=True
    )
    summary_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)

    rule = relationship("Rule", back_populates="summaries")
