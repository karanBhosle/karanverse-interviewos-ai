from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKey

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class VisualFeatureSummary(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "visual_feature_summaries"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True
    )
    feature_type: Mapped[str] = mapped_column(String(60), index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interval_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usable_frames: Mapped[int] = mapped_column(Integer, default=0)
    quality_indicators: Mapped[dict] = mapped_column(JSONType, default=dict)
    algorithm_version: Mapped[str] = mapped_column(String(40), default="opencv-haar-v1")
    processing_status: Mapped[str] = mapped_column(String(30), default="ok")
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
