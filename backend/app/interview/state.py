from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class InterviewGraphState(BaseModel):
    session_id: str
    user_id: str
    mode: str
    difficulty: str
    duration_minutes: int
    target_role: str = "Data Scientist"
    seniority: str = "mid"
    resume_summary: dict[str, Any] = Field(default_factory=dict)
    job_alignment: dict[str, Any] = Field(default_factory=dict)
    prior_gaps: list[str] = Field(default_factory=list)
    planned_question_keys: list[str] = Field(default_factory=list)
    asked_question_keys: list[str] = Field(default_factory=list)
    covered_competencies: list[str] = Field(default_factory=list)
    uncovered_competencies: list[str] = Field(default_factory=list)
    current_question: dict[str, Any] | None = None
    current_answer: str | None = None
    last_evaluation: dict[str, Any] | None = None
    follow_up_count: int = 0
    max_follow_ups: int = 2
    max_questions: int = 6
    llm_calls_used: int = 0
    tokens_used: int = 0
    max_llm_calls: int = 20
    max_tokens: int = 80_000
    provider_available: bool = False
    status: Literal["planning", "asking", "evaluating", "follow_up", "aggregating", "complete", "failed"] = "planning"
    errors: list[str] = Field(default_factory=list)
    skill_gaps: list[dict[str, Any]] = Field(default_factory=list)
    learning_plan: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    retrieved_evidence: list[dict[str, Any]] = Field(default_factory=list)
