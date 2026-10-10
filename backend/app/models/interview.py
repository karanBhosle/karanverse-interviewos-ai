from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKey

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class InterviewPlan(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "interview_plans"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True)
    target_role: Mapped[str] = mapped_column(String(160))
    seniority: Mapped[str] = mapped_column(String(40), default="mid")
    mode: Mapped[str] = mapped_column(String(40))
    difficulty: Mapped[str] = mapped_column(String(20))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    webcam_assisted: Mapped[bool] = mapped_column(Boolean, default=False)
    planned_questions: Mapped[list] = mapped_column(JSONType, default=list)
    planner_notes: Mapped[str] = mapped_column(Text, default="")


class InterviewSession(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "interview_sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("interview_plans.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    mode: Mapped[str] = mapped_column(String(40))
    difficulty: Mapped[str] = mapped_column(String(20))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    webcam_assisted: Mapped[bool] = mapped_column(Boolean, default=False)
    visual_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    covered_competencies: Mapped[list] = mapped_column(JSONType, default=list)
    uncovered_competencies: Mapped[list] = mapped_column(JSONType, default=list)
    asked_question_keys: Mapped[list] = mapped_column(JSONType, default=list)
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls_used: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    graph_state: Mapped[dict] = mapped_column(JSONType, default=dict)
    report_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    provider_available: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="sessions")
    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")
    answers = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")


class InterviewQuestion(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "interview_questions"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True)
    question_key: Mapped[str] = mapped_column(String(80), index=True)
    topic: Mapped[str] = mapped_column(String(80))
    difficulty: Mapped[str] = mapped_column(String(20))
    prompt: Mapped[str] = mapped_column(Text)
    learning_objective: Mapped[str] = mapped_column(Text)
    expected_concepts: Mapped[list] = mapped_column(JSONType, default=list)
    rubric_version: Mapped[str] = mapped_column(String(20), default="v1")
    follow_up_of_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    reference_guidance: Mapped[str] = mapped_column(Text, default="")
    hints: Mapped[list] = mapped_column(JSONType, default=list)
    help_revealed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("InterviewSession", back_populates="questions")


class EvaluationRubric(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "evaluation_rubrics"

    question_key: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[str] = mapped_column(String(20), default="v1")
    question_type: Mapped[str] = mapped_column(String(40))
    dimensions: Mapped[list] = mapped_column(JSONType)


class InterviewAnswer(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "interview_answers"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("interview_questions.id", ondelete="CASCADE"), index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_provenance: Mapped[str] = mapped_column(String(40), default="typed")
    filler_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pause_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    challenged: Mapped[bool] = mapped_column(Boolean, default=False)
    challenge_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    session = relationship("InterviewSession", back_populates="answers")
    evaluation = relationship("AnswerEvaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")


class AnswerEvaluation(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "answer_evaluations"

    answer_id: Mapped[UUID] = mapped_column(ForeignKey("interview_answers.id", ondelete="CASCADE"), unique=True)
    rubric_version: Mapped[str] = mapped_column(String(20))
    dimension_scores: Mapped[list] = mapped_column(JSONType)
    evidence_excerpts: Mapped[list] = mapped_column(JSONType, default=list)
    missing_concepts: Mapped[list] = mapped_column(JSONType, default=list)
    incorrect_claims: Mapped[list] = mapped_column(JSONType, default=list)
    feedback: Mapped[str] = mapped_column(Text)
    suggested_stronger_answer: Mapped[str] = mapped_column(Text)
    follow_up_recommendation: Mapped[str] = mapped_column(String(40))
    evaluation_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    evaluation_version: Mapped[str] = mapped_column(String(20), default="v1")
    provenance: Mapped[str] = mapped_column(String(60))
    weighted_score: Mapped[float] = mapped_column(Float)
    llm_raw_valid: Mapped[bool] = mapped_column(Boolean, default=False)

    answer = relationship("InterviewAnswer", back_populates="evaluation")
