from __future__ import annotations

import re
from typing import Any

from app.resume.ontology import normalize_skill

SOFT_SKILLS = {
    "adaptability",
    "communication",
    "teamwork",
    "leadership",
    "creativity",
    "collaboration",
    "flexibility",
    "motivation",
    "work ethic",
    "time management",
    "problem solving",
    "critical thinking",
    "attention to detail",
    "ownership",
    "curiosity",
}

RELATED_FAMILIES = (
    {"retrieval augmented generation", "vector databases", "bm25", "hybrid search", "keyword search", "similarity search"},
    {"langgraph", "langchain", "langsmith", "agentic ai"},
    {"python", "fastapi", "pandas", "numpy", "pydantic"},
    {"large language models", "prompt engineering", "transformers", "generative ai"},
    {"computer vision", "opencv", "vision models"},
)


def usable_interview_term(skill: str) -> bool:
    text = " ".join((skill or "").lower().split())
    if len(text) < 3:
        return False
    if text in SOFT_SKILLS:
        return False
    if re.fullmatch(r"[\d\W]+", text):
        return False
    if text.endswith(("&", ":", "-", "/", ",", "|")):
        return False
    if "&" in text or text.endswith(":") or re.search(r":\s*\w+\s*&", text):
        return False
    if re.search(r"\b101\b", text):
        return False
    if re.search(r"\bby (anthropic|openai|google|meta|amazon|microsoft)\b", text):
        return False
    if text in {"the", "and", "or", "with", "from", "for", "this", "that"}:
        return False
    return True


def prompt_is_clean(prompt: str) -> bool:
    text = " ".join((prompt or "").split())
    if len(text) < 12:
        return False
    if re.search(r"[:&|]\s*$", text):
        return False
    if re.search(r"\b\w+\s*&\s+(to|for|on|in)\b", text):
        return False
    if "framework &" in text.lower() or "fluency:" in text.lower():
        return False
    return True


def prompts_match(left: str | None, right: str | None) -> bool:
    a = " ".join((left or "").lower().split())
    b = " ".join((right or "").lower().split())
    return bool(a and a == b)


def comparison_is_grounded(prompt: str, keywords: list[str]) -> bool:
    match = re.search(r"difference between (.+?) and (.+?)(?:\s+to|\s+for|\?|$)", prompt or "", re.I)
    if not match:
        return True
    left, right = match.group(1).strip(), match.group(2).strip()
    if not usable_interview_term(left) or not usable_interview_term(right):
        return False
    allowed = {normalize_skill(item) or item.lower() for item in keywords if usable_interview_term(item)}
    left_key = normalize_skill(left) or left.lower()
    right_key = normalize_skill(right) or right.lower()
    if left_key not in allowed or right_key not in allowed:
        return False
    for family in RELATED_FAMILIES:
        if left_key in family and right_key in family:
            return True
    return False


def resume_touchpoints(summary: dict[str, Any] | None) -> dict[str, Any]:
    data = summary or {}
    skills = [str(item).strip() for item in (data.get("technologies") or []) if str(item).strip()]
    projects: list[str] = []
    for project in data.get("projects") or []:
        name = str(project.get("name") or "").strip()
        detail = " ".join(str(item) for item in (project.get("details") or [])[:2]).strip()
        label = name or detail
        if label:
            projects.append(label[:160])
    achievements = [
        str(item.get("text") or "").strip()[:180]
        for item in (data.get("achievements") or [])
        if str(item.get("text") or "").strip()
    ]
    roles = [
        f"{item.get('title', '')} at {item.get('organization', '')}".strip(" at")
        for item in (data.get("roles") or [])
        if item.get("title") or item.get("organization")
    ]
    return {
        "skills": skills[:20],
        "projects": projects[:8],
        "achievements": achievements[:6],
        "roles": roles[:4],
    }


def job_touchpoints(context: dict[str, Any] | None) -> dict[str, Any]:
    data = context or {}
    requirements = []
    for item in data.get("requirements") or []:
        skill = str(item.get("skill") or "").strip()
        if not skill:
            continue
        requirements.append(
            {
                "skill": skill,
                "description": str(item.get("description") or skill).strip()[:220],
                "status": str(item.get("status") or "unknown"),
            }
        )
    missing = [str(item).strip() for item in (data.get("missing") or []) if str(item).strip()]
    if not missing:
        missing = [item["skill"] for item in requirements if item["status"] == "missing"]
    overlap = [str(item).strip() for item in (data.get("strong") or data.get("overlap") or []) if str(item).strip()]
    if not overlap:
        overlap = [item["skill"] for item in requirements if item["status"] in {"strong", "partial", "overlap"}]
    return {
        "title": str(data.get("title") or "this role").strip() or "this role",
        "company": str(data.get("company") or "").strip(),
        "requirements": requirements[:16],
        "missing": missing[:10],
        "overlap": overlap[:10],
    }


def _skill_set(values: list[str]) -> set[str]:
    return {normalize_skill(item) for item in values if item}


def build_mixed_questions(
    *,
    resume_summary: dict[str, Any] | None,
    job_context: dict[str, Any] | None,
    mode: str,
    difficulty: str,
    budget: int,
    target_role: str,
) -> list[dict[str, Any]]:
    resume = resume_touchpoints(resume_summary)
    job = job_touchpoints(job_context)
    role = job["title"] if job["title"] != "this role" else target_role
    resume_norm = _skill_set(resume["skills"])
    selected: list[dict[str, Any]] = []

    overlap = list(job["overlap"])
    if not overlap:
        for req in job["requirements"]:
            if normalize_skill(req["skill"]) in resume_norm:
                overlap.append(req["skill"])
    missing = list(job["missing"])
    if not missing:
        for req in job["requirements"]:
            if normalize_skill(req["skill"]) not in resume_norm:
                missing.append(req["skill"])

    keywords: list[str] = []
    seen_skills: set[str] = set()
    for skill in [
        *resume["skills"],
        *overlap,
        *(item["skill"] for item in job["requirements"]),
        *missing,
    ]:
        key = normalize_skill(skill) or skill.lower()
        if not key or key in seen_skills or not usable_interview_term(skill):
            continue
        seen_skills.add(key)
        keywords.append(skill)
    if not keywords:
        keywords = [role]

    projects = list(resume["projects"])
    if not projects:
        projects = list(resume["achievements"]) or list(resume["roles"]) or ["a project on your resume"]

    jd_topics = [
        item["skill"]
        for item in job["requirements"]
        if usable_interview_term(item["skill"])
    ] or [item for item in missing if usable_interview_term(item)] or keywords
    python_anchor = projects[0] if projects else resume["roles"][0] if resume["roles"] else role

    def add(kind: str, question: dict[str, Any]) -> None:
        if len(selected) >= budget:
            return
        if not prompt_is_clean(question.get("prompt") or ""):
            return
        if any(item["question_key"] == question["question_key"] or item["prompt"] == question["prompt"] for item in selected):
            return
        selected.append({**question, "kind": kind})

    for index in range(5):
        skill = keywords[index % len(keywords)]
        other = next((item for item in keywords if item.lower() != skill.lower()), None)
        keyword_prompts = [
            f"In your own words, what is {skill}, and where have you used it?",
            (
                f"How would you explain the difference between {skill} and {other} "
                f"to someone joining this {role} team?"
                if other and comparison_is_grounded(
                    f"difference between {skill} and {other}",
                    keywords,
                )
                else f"How would you explain {skill} to someone new on this {role} team?"
            ),
            f"Why would a {role} choose to use {skill} instead of a simpler approach?",
            f"When would you decide not to use {skill} in a {role} project?",
            f"How does {skill} show up in the day-to-day work of this {role} role?",
        ]
        add(
            "keyword",
            {
                "question_key": f"mix_keyword_{index}_{normalize_skill(skill)[:20] or index}",
                "topic": normalize_skill(skill) or "keyword",
                "difficulty": "easy",
                "prompt": keyword_prompts[index],
                "learning_objective": f"Check that the candidate can explain {skill} in context.",
                "expected_concepts": [skill],
                "hints": [f"Define {skill} in one sentence, then point to one use."],
                "reference_guidance": f"A strong answer defines {skill} and ties it to real work.",
                "rubric_type": "technical",
                "modes": [mode, "mixed"],
            },
        )

    project_angles = [
        lambda project: (
            f"Walk me through {project}. What problem were you solving, what did you own, "
            "and what changed because of your work?"
        ),
        lambda project: (
            f"If you rebuilt {project} for this {role} role, what would you keep and what would you change?"
        ),
        lambda project: (
            f"What was the hardest technical decision on {project}, and how did you make it?"
        ),
    ]
    for index in range(3):
        project = projects[index % len(projects)]
        add(
            "project",
            {
                "question_key": f"mix_project_{index}",
                "topic": "project_ownership",
                "difficulty": difficulty,
                "prompt": project_angles[index](project),
                "learning_objective": f"Deep-dive a resume project for the {role} conversation.",
                "expected_concepts": ["problem", "ownership", "result"],
                "hints": ["Problem, your part, and one concrete change."],
                "reference_guidance": "Interviewers want ownership, not a recap of the bullet.",
                "rubric_type": "behavioral",
                "modes": [mode, "mixed"],
            },
        )

    job_angles = [
        lambda skill: (
            f"This {role} role mentions {skill}. Have you worked on that? "
            "If yes, walk me through the project. If not, how would you ramp up?"
        ),
        lambda skill: (
            f"The job description asks for {skill}. "
            f"Which project from your resume is the closest, and what would you still need to learn?"
        ),
    ]
    for index in range(2):
        skill = jd_topics[index % len(jd_topics)]
        add(
            "job",
            {
                "question_key": f"mix_job_{index}_{normalize_skill(skill)[:20] or index}",
                "topic": normalize_skill(skill) or "job_requirement",
                "difficulty": "easy",
                "prompt": job_angles[index](skill),
                "learning_objective": f"Probe {skill} from the job description.",
                "expected_concepts": [skill, "project", "ramp-up"],
                "hints": [f"Yes or no on {skill}, then one project or a 30-day plan."],
                "reference_guidance": "A good JD answer is honest and specific.",
                "rubric_type": "technical",
                "modes": [mode, "mixed"],
            },
        )

    add(
        "python",
        {
            "question_key": "mix_python_usage",
            "topic": "python",
            "difficulty": difficulty,
            "prompt": (
                f"How have you used Python on {python_anchor} — which libraries or patterns, and why those?"
            ),
            "learning_objective": "Connect Python practice to a resume project.",
            "expected_concepts": ["python", "libraries", "trade-off"],
            "hints": ["Name the library or pattern and the constraint it solved."],
            "reference_guidance": "A strong Python answer is specific to the work, not a language tour.",
            "rubric_type": "technical",
            "modes": [mode, "mixed"],
        },
    )
    add(
        "python",
        {
            "question_key": "mix_python_debug",
            "topic": "python",
            "difficulty": difficulty,
            "prompt": (
                f"If a Python script for this {role} work started failing in production, "
                "how would you debug it and what would you harden first?"
            ),
            "learning_objective": "Check practical Python debugging for the target role.",
            "expected_concepts": ["python", "debugging", "production"],
            "hints": ["Reproduce, isolate, then name one hardening step."],
            "reference_guidance": "Look for a concrete debug loop, not generic advice.",
            "rubric_type": "technical",
            "modes": [mode, "mixed"],
        },
    )

    return selected[:budget]


def adapt_bank_prompt(prompt: str, *, target_role: str, job_title: str | None, resume_skill: str | None) -> str:
    role = job_title or target_role
    lead = f"For this {role} conversation, "
    if resume_skill:
        lead += f"and given your {resume_skill} background, "
    return f"{lead}{prompt[0].lower() + prompt[1:]}" if prompt else prompt
