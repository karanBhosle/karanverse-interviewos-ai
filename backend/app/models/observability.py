from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKey

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class InvestigationRun(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "investigation_runs"

    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    input_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str] = mapped_column(String(60))
    resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONType, default=dict)
