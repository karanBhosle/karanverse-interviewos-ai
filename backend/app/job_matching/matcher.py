from __future__ import annotations

from typing import Any

STRENGTH_SCORES = {
    "demonstrated": 1.0,
    "keyword_presence": 0.45,
    "missing": 0.0,
}

STATUS_FROM_STRENGTH = {
    "demonstrated": "strong",
    "keyword_presence": "partial",
    "missing": "missing",
}


def match_requirements(
    requirements: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_by_skill: dict[str, dict[str, Any]] = {}
    for row in evidence_rows:
        skill = row["skill_normalized"]
        current = evidence_by_skill.get(skill)
        if current is None or _rank(row["evidence_kind"]) > _rank(current["evidence_kind"]):
            evidence_by_skill[skill] = row

    items: list[dict[str, Any]] = []
    weighted_total = 0.0
    weighted_earned = 0.0
    counts = {"strong": 0, "partial": 0, "missing": 0}

    for requirement in requirements:
        skill = requirement["skill"]
        evidence = evidence_by_skill.get(skill)
        strength = evidence["evidence_kind"] if evidence else "missing"
        status = STATUS_FROM_STRENGTH[strength]
        weight = float(requirement.get("weight") or 1.0)
        weighted_total += weight
        weighted_earned += weight * STRENGTH_SCORES[strength]
        counts[status] += 1
        items.append(
            {
                "requirement_key": requirement["requirement_key"],
                "skill": skill,
                "description": requirement["description"],
                "importance": requirement["importance"],
                "weight": weight,
                "evidence_found": evidence["evidence_text"] if evidence else None,
                "evidence_source": (
                    f"{evidence['source_section']} p.{evidence.get('source_page')}" if evidence else None
                ),
                "evidence_strength": strength,
                "matching_status": status,
                "follow_up_questions": _follow_ups(skill, status),
            }
        )

    score = round((weighted_earned / weighted_total) * 100, 1) if weighted_total else 0.0
    explanation = (
        "This score measures documented alignment between resume evidence and the selected "
        "job description. It is not a probability of being hired. Demonstrated project or "
        "outcome evidence is weighted more heavily than keyword presence."
    )
    return {
        "alignment_score": score,
        "score_explanation": explanation,
        "strong_count": counts["strong"],
        "partial_count": counts["partial"],
        "missing_count": counts["missing"],
        "items": items,
    }


def _rank(kind: str) -> int:
    return {"missing": 0, "keyword_presence": 1, "demonstrated": 2}.get(kind, 0)


def _follow_ups(skill: str, status: str) -> list[str]:
    if status == "missing":
        return [f"Describe a project where you would apply {skill} if you have not used it yet."]
    if status == "partial":
        return [f"Walk through a concrete implementation decision you made with {skill}."]
    return [f"What trade-offs did you accept when using {skill} in production?"]
