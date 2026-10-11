from __future__ import annotations

from typing import Any

from app.interview.bank import QUESTION_BANK, get_question

FOLLOW_UP_PROMPTS = {
    "probe_missing": "I like that direction. Stay with me for a second — how does {concept} change what you just said?",
    "implementation": "Love that direction. Walk me through how you would actually implement the core of it.",
    "tradeoffs": "Good. In production, what trade-off would make you choose a different approach?",
    "failure_scenario": "Alright, plot twist: this breaks in production. How do you catch it, and what do you change?",
    "project_example": "Bring it home with a real project. What constraint were you under, and what did you do?",
    "increase_difficulty": "Nice. Now raise the stakes: higher scale or tighter latency. What changes?",
}


def decide_follow_up(
    question: dict[str, Any],
    evaluation: dict[str, Any],
    *,
    follow_up_count: int,
    max_follow_ups: int,
    asked_keys: list[str],
) -> dict[str, Any] | None:
    if follow_up_count >= max_follow_ups:
        return None
    if evaluation.get("skip_follow_up"):
        return None
    recommendation = evaluation["payload"].follow_up_recommendation
    if recommendation == "next_competency":
        return None
    missing = evaluation["payload"].missing_concepts
    concept = missing[0] if missing else "that concept"
    prompt = FOLLOW_UP_PROMPTS.get(recommendation, FOLLOW_UP_PROMPTS["probe_missing"]).format(concept=concept)
    key = f"{question['question_key']}_fu_{follow_up_count + 1}"
    if key in asked_keys:
        return None
    return {
        "question_key": key,
        "topic": question["topic"],
        "modes": question.get("modes", []),
        "difficulty": question.get("difficulty", "medium"),
        "prompt": prompt,
        "learning_objective": f"Probe {recommendation} after {question['question_key']}.",
        "expected_concepts": missing or question.get("expected_concepts", []),
        "hints": [],
        "reference_guidance": question.get("reference_guidance", ""),
        "rubric_type": question.get("rubric_type", "technical"),
        "parent_key": question["question_key"],
    }


def next_unasked_question(mode: str, asked_keys: list[str], uncovered: list[str]) -> dict[str, Any] | None:
    pool = [q for q in QUESTION_BANK if mode in q["modes"] or (mode == "mixed" and "mixed" in q["modes"])]
    for topic in uncovered:
        for question in pool:
            if question["topic"] == topic and question["question_key"] not in asked_keys:
                return question
    for question in pool:
        if question["question_key"] not in asked_keys:
            return question
    return None


def question_or_none(question_key: str) -> dict[str, Any] | None:
    return get_question(question_key)
