from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKey

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class EvidenceDocument(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "evidence_documents"

    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    source_type: Mapped[str] = mapped_column(String(40))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_text: Mapped[str] = mapped_column(Text)

    chunks = relationship("EvidenceChunk", back_populates="document", cascade="all, delete-orphan")


class EvidenceChunk(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "evidence_chunks"

    document_id: Mapped[UUID] = mapped_column(ForeignKey("evidence_documents.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONType, default=dict)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    document = relationship("EvidenceDocument", back_populates="chunks")
