from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from app.resume.ontology import SKILL_ALIASES, normalize_skill

IMPORTANCE_HINTS = {
    "required": "required",
    "must": "required",
    "strong": "core",
    "experience with": "core",
    "preferred": "preferred",
    "nice to have": "preferred",
    "plus": "preferred",
}

REQUIREMENT_LINE = re.compile(r"^\s*(?:[-*•]|\d+\.)\s+(?P<text>.+)$", re.M)

KNOWN_COMPETENCIES = (
    "python",
    "sql",
    "machine learning",
    "deep learning",
    "statistics",
    "large language models",
    "retrieval augmented generation",
    "agentic ai",
    "langgraph",
    "system design",
    "fastapi",
    "docker",
    "aws",
    "experimentation",
    "computer vision",
    "natural language processing",
    "mlops",
    "postgresql",
    "transformers",
    "prompt engineering",
)


def infer_importance(text: str) -> tuple[str, float]:
    lowered = text.lower()
    for hint, label in IMPORTANCE_HINTS.items():
        if hint in lowered:
            weight = {"required": 1.5, "core": 1.2, "preferred": 0.7}[label]
            return label, weight
    return "core", 1.0


def extract_requirements(job_text: str) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(skill: str, description: str, importance: str | None = None, weight: float | None = None) -> None:
        canon = normalize_skill(skill)
        if not canon or canon in seen:
            return
        inferred, inferred_weight = infer_importance(description)
        seen.add(canon)
        requirements.append(
            {
                "requirement_key": f"req_{uuid4().hex[:8]}",
                "skill": canon,
                "description": description,
                "importance": importance or inferred,
                "weight": weight if weight is not None else inferred_weight,
                "provenance": "job_requirement_inference",
            }
        )

    for match in REQUIREMENT_LINE.finditer(job_text):
        text = match.group("text").strip()
        found = _skills_in_text(text)
        if not found:
            primary = _primary_skill(text)
            if primary:
                found = [primary]
        for skill in found:
            add(skill, text)
    lowered = job_text.lower()
    for competency in KNOWN_COMPETENCIES:
        if competency in lowered:
            add(competency, f"Job description mentions {competency}.")
    for alias, canon in SKILL_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            add(canon, f"Job description mentions {alias}.")
    return requirements[:24]


def _skills_in_text(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for competency in KNOWN_COMPETENCIES:
        if competency in lowered:
            found.append(competency)
    for alias, canon in SKILL_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered) and canon not in found:
            found.append(canon)
    return found


def _primary_skill(text: str) -> str | None:
    found = _skills_in_text(text)
    if found:
        return found[0]
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.]{1,30}", text)
    if tokens:
        return normalize_skill(tokens[0])
    return None
