from __future__ import annotations

from typing import Any

from app.interview.bank import MODE_TOPICS, questions_for_mode
from app.interview.context import adapt_bank_prompt, build_mixed_questions, prompts_match
from app.interview.question_gen import INTERVIEW_QUESTION_COUNT, practice_level


def _question_out(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_key": question["question_key"],
        "topic": question.get("topic", "general"),
        "difficulty": question.get("difficulty", "medium"),
        "prompt": question["prompt"],
        "learning_objective": question.get("learning_objective", ""),
        "expected_concepts": question.get("expected_concepts") or [],
        "hints": question.get("hints") or [],
        "reference_guidance": question.get("reference_guidance") or "",
        "rubric_type": question.get("rubric_type", "technical"),
        "modes": question.get("modes") or [],
    }


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
    resume_summary: dict[str, Any] | None = None,
    job_context: dict[str, Any] | None = None,
    generated_questions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    topics = list(MODE_TOPICS.get(mode, MODE_TOPICS["mixed"]))
    prioritized = []
    for source in (prior_gaps or []) + (missing_requirements or []):
        if source in topics and source not in prioritized:
            prioritized.append(source)
    uncovered = prioritized + [topic for topic in topics if topic not in prioritized]
    level = practice_level(difficulty)
    contextual = bool(resume_summary or job_context or generated_questions)
    budget = INTERVIEW_QUESTION_COUNT if contextual else max(3, min(8, duration_minutes // 8 or 3))
    selected = list(generated_questions or [])
    if not selected:
        selected = build_mixed_questions(
            resume_summary=resume_summary,
            job_context=job_context,
            mode=mode,
            difficulty=level,
            budget=budget,
            target_role=target_role,
        )
    if contextual and len(selected) < INTERVIEW_QUESTION_COUNT:
        filler = build_mixed_questions(
            resume_summary=resume_summary,
            job_context=job_context,
            mode=mode,
            difficulty=level,
            budget=INTERVIEW_QUESTION_COUNT,
            target_role=target_role,
        )
        used_prompts = {item["prompt"].lower() for item in selected}
        used_keys_fill = {item["question_key"] for item in selected}
        for item in filler:
            if item["question_key"] in used_keys_fill or item["prompt"].lower() in used_prompts:
                continue
            selected.append(item)
            used_keys_fill.add(item["question_key"])
            used_prompts.add(item["prompt"].lower())
            if len(selected) >= INTERVIEW_QUESTION_COUNT:
                break
    used_keys = {item["question_key"] for item in selected}
    used_topics = {item["topic"] for item in selected}
    easy_pool = questions_for_mode(mode, "easy")
    medium_pool = questions_for_mode(mode, "medium")
    pool = easy_pool + [item for item in medium_pool if item["question_key"] not in {q["question_key"] for q in easy_pool}]
    job_title = (job_context or {}).get("title")
    resume_skill = (resume_skills or [None])[0]
    if not contextual:
        for topic in uncovered:
            match = next((q for q in pool if q["topic"] == topic and q["question_key"] not in used_keys), None)
            if match:
                adapted = {**match, "prompt": adapt_bank_prompt(match["prompt"], target_role=target_role, job_title=job_title, resume_skill=resume_skill)}
                selected.append(adapted)
                used_keys.add(match["question_key"])
                used_topics.add(topic)
            if len(selected) >= budget:
                break
        for question in pool:
            if question["question_key"] in used_keys:
                continue
            adapted = {
                **question,
                "prompt": adapt_bank_prompt(question["prompt"], target_role=target_role, job_title=job_title, resume_skill=resume_skill),
            }
            selected.append(adapted)
            used_keys.add(question["question_key"])
            if len(selected) >= budget:
                break
    notes = (
        f"Plan for a {seniority} {target_role} {mode.replace('_', ' ')} interview. "
        "Twelve questions: five keyword, three resume projects, two job-description probes, and two Python. "
        "They are generated from the resume and JD and only asked live. "
        "If the candidate cannot answer, the interviewer moves on immediately. "
        "Reference answers stay hidden until the candidate asks for help."
    )
    if resume_skills:
        notes += f" Resume skills considered: {', '.join(resume_skills[:8])}."
    if missing_requirements:
        notes += f" Job gaps probed: {', '.join(missing_requirements[:6])}."
    unique: list[dict[str, Any]] = []
    for item in selected[:budget]:
        if any(prompts_match(item.get("prompt"), existing.get("prompt")) for existing in unique):
            continue
        unique.append(item)
    return {
        "planned_questions": [_question_out(q) for q in unique],
        "uncovered_competencies": [q["topic"] for q in unique],
        "planner_notes": notes,
        "max_questions": max(len(unique), 1),
    }
