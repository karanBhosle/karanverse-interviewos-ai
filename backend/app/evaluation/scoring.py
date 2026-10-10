from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.interview.bank import dimensions_for

FILLER_WORDS = {"um", "uh", "like", "you know", "sort of", "kind of"}


class DimensionScore(BaseModel):
    id: str
    label: str
    weight: float = Field(gt=0)
    score: float = Field(ge=0, le=5)
    justification: str
    answer_excerpt: str = ""


class ModelEvaluationPayload(BaseModel):
    dimensions: list[DimensionScore]
    missing_concepts: list[str] = Field(default_factory=list)
    incorrect_claims: list[str] = Field(default_factory=list)
    feedback: str
    suggested_stronger_answer: str
    follow_up_recommendation: str = "next_competency"

    @field_validator("follow_up_recommendation")
    @classmethod
    def known_follow_up(cls, value: str) -> str:
        allowed = {
            "probe_missing",
            "implementation",
            "tradeoffs",
            "failure_scenario",
            "project_example",
            "increase_difficulty",
            "next_competency",
        }
        if value not in allowed:
            raise ValueError("unsupported follow-up recommendation")
        return value


def weighted_score(dimensions: list[DimensionScore]) -> float:
    total_weight = sum(item.weight for item in dimensions)
    if total_weight <= 0:
        raise ValueError("Rubric weights must be positive")
    raw = sum(item.score * item.weight for item in dimensions) / total_weight
    return round((raw / 5.0) * 100.0, 2)


_STOP = {"vs", "or", "and", "the", "a", "an", "of", "to", "for", "as"}


def _token_present(haystack: str, token: str) -> bool:
    variants = {token, f"{token}s", token.rstrip("s")}
    return any(variant and variant in haystack for variant in variants)


def concept_hits(answer: str, expected_concepts: list[str]) -> tuple[list[str], list[str]]:
    lowered = answer.lower()
    found: list[str] = []
    missing: list[str] = []
    for concept in expected_concepts:
        tokens = [token for token in re.split(r"\s+", concept.lower()) if token]
        distinctive = [token for token in tokens if token not in _STOP]
        if concept.lower() in lowered:
            found.append(concept)
        elif distinctive and all(_token_present(lowered, token) for token in distinctive):
            found.append(concept)
        elif any(_token_present(lowered, token) for token in distinctive) and len(distinctive) == 1:
            found.append(concept)
        else:
            missing.append(concept)
    return found, missing


def deterministic_evaluation(question: dict[str, Any], answer: str) -> dict[str, Any]:
    expected = question.get("expected_concepts") or []
    found, missing = concept_hits(answer, expected)
    coverage = len(found) / len(expected) if expected else 0.0
    structure_bonus = 0.15 if len(answer.split()) >= 80 else 0.0
    example_bonus = 0.1 if any(word in answer.lower() for word in ("for example", "in my project", "we deployed")) else 0.0
    base = min(5.0, max(1.0, coverage * 4.2 + structure_bonus + example_bonus + 0.4))
    dimensions = []
    for item in dimensions_for(question):
        score = base
        if item["id"] in {"examples_evidence", "action_ownership"} and example_bonus == 0:
            score = max(1.0, base - 1.2)
        if item["id"] == "communication_structure" and structure_bonus == 0:
            score = max(1.0, base - 0.8)
        excerpt = _excerpt_for_concept(answer, found[0]) if found else answer[:180]
        dimensions.append(
            DimensionScore(
                id=item["id"],
                label=item["label"],
                weight=item["weight"],
                score=round(min(5.0, score), 2),
                justification=(
                    f"Deterministic concept coverage found {len(found)}/{len(expected)} expected concepts. "
                    "This is a coverage measurement, not an LLM judgment."
                ),
                answer_excerpt=excerpt,
            )
        )
    recommendation = "probe_missing" if missing else "next_competency"
    feedback = (
        "This score is a deterministic concept-coverage measurement computed in Python. "
        "It is not a validated predictor of job performance and is not an LLM evaluation."
    )
    if found:
        feedback += f" Observed concepts: {', '.join(found)}."
    if missing:
        feedback += f" Missing expected concepts: {', '.join(missing)}."
    payload = ModelEvaluationPayload(
        dimensions=dimensions,
        missing_concepts=missing,
        incorrect_claims=[],
        feedback=feedback,
        suggested_stronger_answer=_stronger_answer(question, missing),
        follow_up_recommendation=recommendation,
    )
    return {
        "payload": payload,
        "weighted_score": weighted_score(payload.dimensions),
        "provenance": "deterministic_concept_coverage",
        "evaluation_model": None,
        "llm_raw_valid": False,
        "found_concepts": found,
    }


def apply_model_payload(
    question: dict[str, Any],
    payload: ModelEvaluationPayload,
    *,
    model_name: str,
) -> dict[str, Any]:
    expected_ids = {item["id"] for item in dimensions_for(question)}
    payload_ids = {item.id for item in payload.dimensions}
    if payload_ids != expected_ids:
        raise ValueError("Model returned dimensions that do not match the rubric")
    return {
        "payload": payload,
        "weighted_score": weighted_score(payload.dimensions),
        "provenance": "llm_interpretation_plus_python_score",
        "evaluation_model": model_name,
        "llm_raw_valid": True,
        "found_concepts": [],
    }


def filler_word_count(text: str) -> int:
    lowered = f" {text.lower()} "
    return sum(lowered.count(f" {word} ") for word in FILLER_WORDS)


def _excerpt_for_concept(answer: str, concept: str) -> str:
    lowered = answer.lower()
    index = lowered.find(concept.lower().split()[0])
    if index < 0:
        return answer[:180]
    start = max(0, index - 40)
    return answer[start : start + 180]


def _stronger_answer(question: dict[str, Any], missing: list[str]) -> str:
    guidance = question.get("reference_guidance", "")
    if missing:
        return f"{guidance} Explicitly cover: {', '.join(missing)}."
    return guidance
