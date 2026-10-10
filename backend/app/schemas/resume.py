from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ResumeSummary(ORMModel):
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    status: str


class ResumeDetail(ResumeSummary):
    latest_version_id: UUID | None = None
    structured: dict[str, Any] | None = None
    extracted_text: str | None = None
    warnings: list[str] = Field(default_factory=list)


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    company: str | None = None
    seniority: str | None = None
    raw_text: str = Field(min_length=8, max_length=80_000)


class JobRequirementOut(ORMModel):
    id: UUID
    requirement_key: str
    skill: str
    description: str
    importance: str
    weight: float


class JobDetail(ORMModel):
    id: UUID
    title: str
    company: str | None
    seniority: str | None
    raw_text: str
    extraction_method: str
    requirements: list[JobRequirementOut]


class JobMatchRequest(BaseModel):
    resume_id: UUID
    job_id: UUID


class JobMatchItemOut(BaseModel):
    skill: str
    description: str
    importance: str
    evidence_found: str | None
    evidence_source: str | None
    evidence_strength: str
    matching_status: str
    follow_up_questions: list[str]


class JobMatchOut(BaseModel):
    id: UUID
    alignment_score: float
    score_explanation: str
    strong_count: int
    partial_count: int
    missing_count: int
    items: list[JobMatchItemOut]
