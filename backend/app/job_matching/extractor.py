from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from app.resume.ontology import normalize_skill

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
    for match in REQUIREMENT_LINE.finditer(job_text):
        text = match.group("text").strip()
        skill = _primary_skill(text)
        if not skill or skill in seen:
            continue
        importance, weight = infer_importance(text)
        seen.add(skill)
        requirements.append(
            {
                "requirement_key": f"req_{uuid4().hex[:8]}",
                "skill": skill,
                "description": text,
                "importance": importance,
                "weight": weight,
                "provenance": "job_requirement_inference",
            }
        )
    for competency in KNOWN_COMPETENCIES:
        if competency in job_text.lower() and competency not in seen:
            seen.add(competency)
            requirements.append(
                {
                    "requirement_key": f"req_{uuid4().hex[:8]}",
                    "skill": competency,
                    "description": f"Job description mentions {competency}.",
                    "importance": "core",
                    "weight": 1.0,
                    "provenance": "job_requirement_inference",
                }
            )
    return requirements[:24]


def _primary_skill(text: str) -> str | None:
    lowered = text.lower()
    for competency in KNOWN_COMPETENCIES:
        if competency in lowered:
            return competency
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.]{1,30}", text)
    if tokens:
        return normalize_skill(tokens[0])
    return None
