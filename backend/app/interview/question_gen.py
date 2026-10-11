from __future__ import annotations

import json
import logging
from typing import Any

from app.interview.context import (
    build_mixed_questions,
    comparison_is_grounded,
    job_touchpoints,
    prompt_is_clean,
    resume_touchpoints,
)
from app.services.llm import CompatibleLLMProvider, LLMError, parse_json_object

logger = logging.getLogger(__name__)

INTERVIEW_QUESTION_COUNT = 12
QUESTION_MIX = (("keyword", 5), ("project", 3), ("job", 2), ("python", 2))
KIND_ALIASES = {
    "keyword": "keyword",
    "concept": "keyword",
    "definition": "keyword",
    "project": "project",
    "resume": "project",
    "job": "job",
    "jd": "job",
    "role": "job",
    "python": "python",
}


def practice_level(difficulty: str) -> str:
    return "easy" if (difficulty or "").lower() == "easy" else "medium"


def _kind_of(item: dict[str, Any], index: int) -> str:
    raw = str(item.get("kind") or item.get("bucket") or "").strip().lower()
    if raw in KIND_ALIASES:
        return KIND_ALIASES[raw]
    topic = str(item.get("topic") or "").strip().lower()
    if "python" in topic:
        return "python"
    if "project" in topic:
        return "project"
    if topic in {"job", "jd", "role"}:
        return "job"
    if topic in {"keyword", "concept"}:
        return "keyword"
    if index < 5:
        return "keyword"
    if index < 8:
        return "project"
    if index < 10:
        return "job"
    return "python"


def _normalize_item(
    item: dict[str, Any],
    *,
    mode: str,
    index: int,
    kind: str,
    keywords: list[str] | None = None,
) -> dict[str, Any] | None:
    prompt = str(item.get("prompt") or "").strip()
    if len(prompt) < 12:
        return None
    if not prompt_is_clean(prompt):
        return None
    if not comparison_is_grounded(prompt, keywords or []):
        return None
    level = str(item.get("difficulty") or "easy").lower()
    if level not in {"easy", "medium"}:
        level = "easy" if kind in {"keyword", "job"} else "medium"
    key = str(item.get("question_key") or f"llm_{kind}_{index}").strip() or f"llm_{kind}_{index}"
    return {
        "question_key": key[:48],
        "topic": str(item.get("topic") or kind).strip() or kind,
        "kind": kind,
        "difficulty": level,
        "prompt": prompt,
        "learning_objective": str(
            item.get("learning_objective") or f"Discuss {item.get('topic') or kind} at a {level} level."
        ),
        "expected_concepts": list(item.get("expected_concepts") or [])[:6],
        "hints": list(item.get("hints") or [])[:3],
        "reference_guidance": str(
            item.get("reference_guidance") or "Keep the answer concrete and tied to the resume or job."
        ),
        "rubric_type": "behavioral" if kind == "project" else "technical",
        "modes": [mode, "mixed"],
    }


def _normalize_generated(
    raw: list[dict[str, Any]],
    *,
    mode: str,
    budget: int,
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {kind: [] for kind, _ in QUESTION_MIX}
    seen_prompts: set[str] = set()
    for index, item in enumerate(raw or []):
        if not isinstance(item, dict):
            continue
        kind = _kind_of(item, index)
        normalized = _normalize_item(item, mode=mode, index=index, kind=kind, keywords=keywords)
        if normalized is None:
            continue
        fold = normalized["prompt"].lower()
        if fold in seen_prompts:
            continue
        seen_prompts.add(fold)
        buckets[kind].append(normalized)
    selected: list[dict[str, Any]] = []
    for kind, quota in QUESTION_MIX:
        selected.extend(buckets[kind][:quota])
        if len(selected) >= budget:
            break
    return selected[:budget]


def _fill_question_slots(
    selected: list[dict[str, Any]],
    *,
    resume_summary: dict[str, Any] | None,
    job_context: dict[str, Any] | None,
    mode: str,
    difficulty: str,
    target_role: str,
) -> list[dict[str, Any]]:
    have = {kind: [] for kind, _ in QUESTION_MIX}
    seen = {item["prompt"].lower() for item in selected}
    for item in selected:
        have[str(item.get("kind") or "keyword")].append(item)
    if sum(len(items) for items in have.values()) < INTERVIEW_QUESTION_COUNT:
        fallback = build_mixed_questions(
            resume_summary=resume_summary,
            job_context=job_context,
            mode=mode,
            difficulty=practice_level(difficulty),
            budget=INTERVIEW_QUESTION_COUNT,
            target_role=target_role,
        )
        for item in fallback:
            kind = str(item.get("kind") or "keyword")
            fold = item["prompt"].lower()
            if fold in seen:
                continue
            have.setdefault(kind, []).append(item)
            seen.add(fold)
    ordered: list[dict[str, Any]] = []
    for kind, quota in QUESTION_MIX:
        ordered.extend(have.get(kind, [])[:quota])
    return ordered[:INTERVIEW_QUESTION_COUNT]


async def generate_resume_jd_questions(
    *,
    resume_summary: dict[str, Any] | None,
    job_context: dict[str, Any] | None,
    mode: str,
    difficulty: str,
    budget: int,
    target_role: str,
    resume_text: str = "",
    provider: CompatibleLLMProvider | None = None,
) -> list[dict[str, Any]]:
    del budget
    llm = provider or CompatibleLLMProvider()
    resume = resume_touchpoints(resume_summary)
    job = job_touchpoints(job_context)
    if provider is None and not getattr(llm, "available", False):
        return _fill_question_slots(
            [],
            resume_summary=resume_summary,
            job_context=job_context,
            mode=mode,
            difficulty=difficulty,
            target_role=target_role,
        )
    system = (
        "You write a live interview question list for one candidate. "
        "Reply with JSON only: {\"questions\": [{\"question_key\": string, \"kind\": "
        "\"keyword\"|\"project\"|\"job\"|\"python\", \"topic\": string, "
        "\"difficulty\": \"easy\"|\"medium\", \"prompt\": string, \"learning_objective\": string, "
        "\"expected_concepts\": [string], \"hints\": [string], \"reference_guidance\": string}]}. "
        "Write exactly 12 questions from THIS resume and job description: "
        "5 kind=keyword, 3 kind=project, 2 kind=job, 2 kind=python. "
        "Keyword questions are short concept checks using terms that actually appear in the resume or JD "
        "(what it is, how two of those terms differ, or why a technique is used). "
        "Project questions are deep-dives into work listed on the resume. "
        "Job questions are short JD probes: have they done a posted requirement, and if yes, which project. "
        "Python questions are practical and tied to this resume and role. "
        "The following are style only. Do not copy them, and do not emit them unless THIS resume or JD "
        "justifies the same idea: a definition question, a comparison of two retrieved terms, "
        "a 'why this storage/tool' question, an agent-framework question, or "
        "'have you worked on <JD skill>? If yes, explain the project.' "
        "Invent new prompts from the provided skills, projects, and requirements. "
        "Never invent employers or metrics. Stay easy-to-intermediate. Each prompt is one spoken question."
    )
    user = json.dumps(
        {
            "target_role": target_role,
            "mode": mode,
            "level": practice_level(difficulty),
            "count": INTERVIEW_QUESTION_COUNT,
            "mix": [{"kind": kind, "count": count} for kind, count in QUESTION_MIX],
            "resume": resume,
            "job": job,
            "resume_excerpt": (resume_text or "")[:4000],
        }
    )
    selected: list[dict[str, Any]] = []
    try:
        result = await llm.complete_json(system=system, user=user, schema_name="resume_jd_questions")
        payload = parse_json_object(result.content)
        questions = payload.get("questions") if isinstance(payload, dict) else None
        if isinstance(questions, list):
            selected = _normalize_generated(
                questions,
                mode=mode,
                budget=INTERVIEW_QUESTION_COUNT,
                keywords=[*resume.get("skills", []), *(item["skill"] for item in job.get("requirements", []))],
            )
    except (LLMError, ValueError, TypeError) as exc:
        logger.warning("Resume/JD question generation fell back: %s", exc)
    return _fill_question_slots(
        selected,
        resume_summary=resume_summary,
        job_context=job_context,
        mode=mode,
        difficulty=difficulty,
        target_role=target_role,
    )
