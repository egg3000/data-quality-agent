import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, UUIDPrimaryKey


class KnowledgeEntry(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "knowledge_entries"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    embedding = mapped_column(Vector(384))
    tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
