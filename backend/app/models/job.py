from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKey

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class JobDescription(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "job_descriptions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(40), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(String(40), default="deterministic")

    user = relationship("User", back_populates="jobs")
    requirements = relationship("JobRequirement", back_populates="job", cascade="all, delete-orphan")
    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")


class JobRequirement(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "job_requirements"

    job_id: Mapped[UUID] = mapped_column(ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True)
    requirement_key: Mapped[str] = mapped_column(String(80), index=True)
    skill: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    importance: Mapped[str] = mapped_column(String(20), default="core")
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    job = relationship("JobDescription", back_populates="requirements")


class JobMatch(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "job_matches"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_version_id: Mapped[UUID] = mapped_column(ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True)
    alignment_score: Mapped[float] = mapped_column(Float)
    score_explanation: Mapped[str] = mapped_column(Text)
    strong_count: Mapped[int] = mapped_column(Integer, default=0)
    partial_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_count: Mapped[int] = mapped_column(Integer, default=0)
    prepared_questions: Mapped[list] = mapped_column(JSONType, default=list)

    job = relationship("JobDescription", back_populates="matches")
    items = relationship("JobMatchItem", back_populates="match", cascade="all, delete-orphan")


class JobMatchItem(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "job_match_items"

    match_id: Mapped[UUID] = mapped_column(ForeignKey("job_matches.id", ondelete="CASCADE"), index=True)
    requirement_id: Mapped[UUID] = mapped_column(ForeignKey("job_requirements.id", ondelete="CASCADE"))
    evidence_found: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    evidence_strength: Mapped[str] = mapped_column(String(20))
    matching_status: Mapped[str] = mapped_column(String(20))
    follow_up_questions: Mapped[list] = mapped_column(JSONType, default=list)

    match = relationship("JobMatch", back_populates="items")
