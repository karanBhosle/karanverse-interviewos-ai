from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKey


class Resume(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "resumes"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40), default="processed")

    user = relationship("User", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")


class ResumeVersion(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "resume_versions"
    __table_args__ = (UniqueConstraint("resume_id", "version_number"),)

    resume_id: Mapped[UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    extracted_text: Mapped[str] = mapped_column(Text)
    structured_json: Mapped[dict] = mapped_column(JSON().with_variant(SQLiteJSON(), "sqlite"))
    extraction_method: Mapped[str] = mapped_column(String(40), default="deterministic")
    ocr_used: Mapped[bool] = mapped_column(default=False)

    resume = relationship("Resume", back_populates="versions")
    evidence = relationship("CandidateSkillEvidence", back_populates="resume_version", cascade="all, delete-orphan")


class CandidateSkillEvidence(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "candidate_skill_evidence"

    resume_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True
    )
    skill_raw: Mapped[str] = mapped_column(String(160))
    skill_normalized: Mapped[str] = mapped_column(String(160), index=True)
    evidence_text: Mapped[str] = mapped_column(Text)
    source_section: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_kind: Mapped[str] = mapped_column(String(40), default="keyword_presence")

    resume_version = relationship("ResumeVersion", back_populates="evidence")
