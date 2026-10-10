from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKey


class SkillGap(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "skill_gaps"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="SET NULL"), nullable=True
    )
    skill: Mapped[str] = mapped_column(String(160), index=True)
    evidence: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    job_relevance: Mapped[str] = mapped_column(String(20), default="medium")
    recurrence: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(30), default="unresolved", index=True)


class LearningPlan(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "learning_plans"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="active")
    summary: Mapped[str] = mapped_column(Text, default="")

    tasks = relationship("LearningTask", back_populates="plan", cascade="all, delete-orphan")


class LearningTask(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "learning_tasks"

    plan_id: Mapped[UUID] = mapped_column(ForeignKey("learning_plans.id", ondelete="CASCADE"), index=True)
    skill_gap_id: Mapped[UUID | None] = mapped_column(ForeignKey("skill_gaps.id", ondelete="SET NULL"), nullable=True)
    skill: Mapped[str] = mapped_column(String(160))
    why_it_matters: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20))
    recommended_reading: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_suggestion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    practice_question: Mapped[str] = mapped_column(Text)
    coding_exercise: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_outcome: Mapped[str] = mapped_column(Text)
    reassessment_criteria: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="unresolved")

    plan = relationship("LearningPlan", back_populates="tasks")
