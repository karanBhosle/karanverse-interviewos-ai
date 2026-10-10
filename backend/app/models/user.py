from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKey


class User(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    resume_retention_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    session_history_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    camera_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    media_storage_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    visual_checklist_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    visual_analysis_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("JobDescription", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
