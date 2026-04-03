import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKey


class Rule(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "rules"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    sql_query: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))

    runs = relationship("RuleRun", back_populates="rule", cascade="all, delete-orphan")
    errors = relationship("RuleError", back_populates="rule", cascade="all, delete-orphan")
    summaries = relationship("ErrorSummary", back_populates="rule", cascade="all, delete-orphan")
