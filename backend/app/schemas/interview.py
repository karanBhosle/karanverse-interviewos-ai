from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.interview.bank import MODES
from app.schemas.common import ORMModel

Mode = Literal[
    "technical_fundamentals",
    "python_coding",
    "machine_learning",
    "genai_llms",
    "rag_hybrid_retrieval",
    "agentic_ai_langgraph",
    "system_design",
    "project_deep_dive",
    "behavioral",
    "mixed",
]


class InterviewPlanCreate(BaseModel):
    resume_id: UUID | None = None
    job_id: UUID | None = None
    target_role: str = "Data Scientist"
    seniority: str = "mid"
    mode: Mode = "mixed"
    difficulty: str = "medium"
    duration_minutes: int = Field(default=30, ge=10, le=90)
    webcam_assisted: bool = False


class InterviewPlanOut(ORMModel):
    id: UUID
    target_role: str
    seniority: str
    mode: str
    difficulty: str
    duration_minutes: int
    webcam_assisted: bool
    planned_questions: list[dict[str, Any]]
    planner_notes: str


class SessionCreate(BaseModel):
    plan_id: UUID
    visual_consent: bool = False
    speech_assisted: bool = True


class QuestionOut(BaseModel):
    id: UUID
    question_key: str
    topic: str
    difficulty: str
    prompt: str
    learning_objective: str
    sequence: int
    hints_available: bool
    help_revealed: bool
    is_follow_up: bool
    reference_guidance: str | None = None


class AnswerSubmit(BaseModel):
    question_id: UUID
    raw_text: str = Field(min_length=1)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    request_help: bool = False
    visual_features: list[dict[str, Any]] | None = None
    transcript_provenance: Literal["typed", "speech_to_text"] = "typed"


class ChallengeRequest(BaseModel):
    note: str = Field(min_length=3, max_length=2000)


class EvaluationOut(BaseModel):
    weighted_score: float
    provenance: str
    evaluation_model: str | None
    rubric_version: str
    dimension_scores: list[dict[str, Any]]
    evidence_excerpts: list[Any]
    missing_concepts: list[str]
    incorrect_claims: list[str]
    feedback: str
    suggested_stronger_answer: str
    follow_up_recommendation: str
    limitations: list[str]


class SessionOut(ORMModel):
    id: UUID
    status: str
    mode: str
    difficulty: str
    duration_minutes: int
    webcam_assisted: bool
    visual_consent: bool
    covered_competencies: list[str]
    uncovered_competencies: list[str]
    follow_up_count: int
    provider_available: bool
    speech_assisted: bool = False
    speech_lexicon: list[str] = Field(default_factory=list)
    current_question: QuestionOut | None = None


class VisualIngest(BaseModel):
    question_id: UUID | None = None
    frames: list[dict[str, Any]] = Field(default_factory=list)
    aggregated_features: list[dict[str, Any]] | None = None
    consent: bool = False


class LearningTaskOut(BaseModel):
    id: UUID
    skill: str
    why_it_matters: str
    priority: str
    recommended_reading: str | None
    search_suggestion: str | None
    practice_question: str
    coding_exercise: str | None
    expected_outcome: str
    reassessment_criteria: str
    status: str


class LearningPlanOut(BaseModel):
    id: UUID
    status: str
    summary: str
    tasks: list[LearningTaskOut]


class SkillGapOut(ORMModel):
    id: UUID
    skill: str
    evidence: str
    why_it_matters: str
    severity: str
    job_relevance: str
    recurrence: int
    status: str
    session_id: UUID | None


assert set(MODES) == set(Mode.__args__)  # type: ignore[attr-defined]
