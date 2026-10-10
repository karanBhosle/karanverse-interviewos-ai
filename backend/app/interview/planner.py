from __future__ import annotations

from typing import Any

from app.interview.bank import MODE_TOPICS, questions_for_mode


def plan_interview(
    *,
    mode: str,
    difficulty: str,
    duration_minutes: int,
    target_role: str,
    seniority: str,
    resume_skills: list[str] | None = None,
    missing_requirements: list[str] | None = None,
    prior_gaps: list[str] | None = None,
) -> dict[str, Any]:
    topics = list(MODE_TOPICS.get(mode, MODE_TOPICS["mixed"]))
    prioritized = []
    for source in (prior_gaps or []) + (missing_requirements or []):
        if source in topics and source not in prioritized:
            prioritized.append(source)
    uncovered = prioritized + [topic for topic in topics if topic not in prioritized]
    budget = max(3, min(8, duration_minutes // 8 or 3))
    pool = questions_for_mode(mode, difficulty)
    selected: list[dict[str, Any]] = []
    used_topics: set[str] = set()
    for topic in uncovered:
        match = next((q for q in pool if q["topic"] == topic and q not in selected), None)
        if match:
            selected.append(match)
            used_topics.add(topic)
        if len(selected) >= budget:
            break
    for question in pool:
        if question not in selected:
            selected.append(question)
        if len(selected) >= budget:
            break
    notes = (
        f"Plan for a {seniority} {target_role} {mode.replace('_', ' ')} interview. "
        "Questions are chosen from a curated bank using resume gaps and job-requirement misses first. "
        "Reference answers stay hidden until the candidate asks for help."
    )
    if resume_skills:
        notes += f" Resume skills considered: {', '.join(resume_skills[:8])}."
    return {
        "planned_questions": [
            {
                "question_key": q["question_key"],
                "topic": q["topic"],
                "difficulty": q["difficulty"],
                "prompt": q["prompt"],
                "learning_objective": q["learning_objective"],
            }
            for q in selected
        ],
        "uncovered_competencies": [q["topic"] for q in selected],
        "planner_notes": notes,
        "max_questions": budget,
    }
