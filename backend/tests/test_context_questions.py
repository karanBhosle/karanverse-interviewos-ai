import pytest

from app.interview.context import (
    build_mixed_questions,
    comparison_is_grounded,
    prompt_is_clean,
    usable_interview_term,
)
from app.interview.graph import InterviewGraph
from app.interview.planner import plan_interview
from app.interview.question_gen import (
    INTERVIEW_QUESTION_COUNT,
    QUESTION_MIX,
    _normalize_generated,
    generate_resume_jd_questions,
    practice_level,
)
from app.interview.state import InterviewGraphState
from app.services.llm import MockLLMProvider


RESUME = {
    "technologies": ["python", "langgraph", "sql"],
    "projects": [{"name": "Interview coach graph", "details": ["Typed LangGraph state", "Fail-closed scoring"]}],
    "achievements": [{"text": "Cut evaluation latency 40% with a hybrid retriever"}],
    "roles": [{"title": "Data Scientist", "organization": "karanVerse"}],
}

JOB = {
    "title": "ML Engineer",
    "company": "Example",
    "requirements": [
        {"skill": "python", "description": "Strong Python", "status": "strong"},
        {"skill": "retrieval augmented generation", "description": "RAG systems", "status": "missing"},
        {"skill": "langgraph", "description": "Agent graphs", "status": "partial"},
        {"skill": "vision models", "description": "Computer vision", "status": "missing"},
    ],
    "missing": ["retrieval augmented generation", "vision models"],
    "strong": ["python"],
    "overlap": ["python", "langgraph"],
}


def _llm_question(kind: str, prompt: str, key: str, difficulty: str = "easy") -> dict:
    return {
        "question_key": key,
        "kind": kind,
        "topic": kind,
        "difficulty": difficulty,
        "prompt": prompt,
    }


@pytest.mark.asyncio
async def test_llm_generates_structured_resume_jd_mix():
    payload = (
        [_llm_question("keyword", f"What is keyword concept {index} from this resume?", f"k{index}") for index in range(5)]
        + [_llm_question("project", f"Walk me through resume project {index} in your own words.", f"p{index}") for index in range(3)]
        + [_llm_question("job", f"Have you worked on job skill {index} from this posting?", f"j{index}") for index in range(2)]
        + [_llm_question("python", f"How did you use Python for case {index} on this work?", f"py{index}") for index in range(2)]
    )
    provider = MockLLMProvider({"questions": payload})
    questions = await generate_resume_jd_questions(
        resume_summary=RESUME,
        job_context=JOB,
        mode="mixed",
        difficulty="hard",
        budget=4,
        target_role="ML Engineer",
        provider=provider,
    )
    assert len(questions) == INTERVIEW_QUESTION_COUNT
    counts = {kind: 0 for kind, _ in QUESTION_MIX}
    for item in questions:
        counts[item["kind"]] += 1
        assert item["difficulty"] in {"easy", "medium"}
    assert counts == dict(QUESTION_MIX)
    assert "keyword concept 0" in questions[0]["prompt"]
    assert all("what is rag" not in item["prompt"].lower() for item in questions)


def test_mixed_questions_follow_live_mix_from_resume_and_job():
    questions = build_mixed_questions(
        resume_summary=RESUME,
        job_context=JOB,
        mode="mixed",
        difficulty="medium",
        budget=INTERVIEW_QUESTION_COUNT,
        target_role="ML Engineer",
    )
    assert len(questions) == INTERVIEW_QUESTION_COUNT
    counts = {kind: 0 for kind, _ in QUESTION_MIX}
    for item in questions:
        counts[item["kind"]] += 1
    assert counts == dict(QUESTION_MIX)
    prompts = " ".join(item["prompt"].lower() for item in questions)
    assert "interview coach graph" in prompts
    assert "python" in prompts
    assert "vision models" in prompts or "retrieval" in prompts


def test_plan_keeps_generated_order_and_count():
    generated = _normalize_generated(
        [
            _llm_question("keyword", "Walk me through your current role in simple terms.", "llm_warmup"),
            _llm_question("keyword", "What is the next keyword from your stack?", "llm_kw2"),
        ],
        mode="mixed",
        budget=INTERVIEW_QUESTION_COUNT,
    )
    plan = plan_interview(
        mode="mixed",
        difficulty="hard",
        duration_minutes=24,
        target_role="ML Engineer",
        seniority="mid",
        resume_summary=RESUME,
        job_context=JOB,
        generated_questions=generated,
    )
    first = plan["planned_questions"][0]
    assert first["question_key"] == "llm_warmup"
    assert plan["max_questions"] == INTERVIEW_QUESTION_COUNT
    assert len(plan["planned_questions"]) == INTERVIEW_QUESTION_COUNT
    assert practice_level("hard") == "medium"


def test_plan_puts_mixed_questions_first():
    plan = plan_interview(
        mode="mixed",
        difficulty="medium",
        duration_minutes=24,
        target_role="ML Engineer",
        seniority="mid",
        resume_skills=["python", "langgraph"],
        missing_requirements=["retrieval augmented generation"],
        resume_summary=RESUME,
        job_context=JOB,
    )
    first = plan["planned_questions"][0]
    assert first["question_key"].startswith("mix_keyword_")
    assert len(plan["planned_questions"]) == INTERVIEW_QUESTION_COUNT


def test_question_generator_uses_planned_mix():
    graph = InterviewGraph()
    planned = plan_interview(
        mode="mixed",
        difficulty="medium",
        duration_minutes=24,
        target_role="ML Engineer",
        seniority="mid",
        resume_summary=RESUME,
        job_context=JOB,
    )["planned_questions"]
    state = InterviewGraphState(
        session_id="s1",
        user_id="u1",
        mode="mixed",
        difficulty="medium",
        duration_minutes=24,
        target_role="ML Engineer",
        planned_question_keys=[item["question_key"] for item in planned],
        planned_questions=planned,
        uncovered_competencies=[item["topic"] for item in planned],
        max_questions=len(planned),
    )
    state = graph.question_generator(state)
    assert state.current_question is not None
    assert state.current_question["question_key"] == planned[0]["question_key"]
    assert "ml engineer" in state.current_question["prompt"].lower() or "resume" in state.current_question["prompt"].lower() or "python" in state.current_question["prompt"].lower()


def test_rejects_unrelated_keyword_comparisons():
    assert not usable_interview_term("adaptability")
    assert not usable_interview_term("101 by anthropic")
    assert not usable_interview_term("ai fluency: framework &")
    assert not prompt_is_clean("How would you explain ai fluency: framework & to someone new on this team?")
    assert usable_interview_term("LangGraph")
    assert not comparison_is_grounded(
        "How would you explain the difference between adaptability and 101 by anthropic to someone joining this team?",
        ["adaptability", "101 by anthropic", "LangGraph"],
    )
    questions = build_mixed_questions(
        resume_summary={
            "technologies": ["adaptability", "101 by anthropic", "LangGraph", "RAG"],
            "projects": [{"name": "Agent graph", "details": ["LangGraph"]}],
            "achievements": [],
            "roles": [],
        },
        job_context={"title": "Gen AI Engineer", "requirements": [], "missing": [], "overlap": []},
        mode="mixed",
        difficulty="easy",
        budget=INTERVIEW_QUESTION_COUNT,
        target_role="Gen AI Engineer",
    )
    prompts = " ".join(item["prompt"].lower() for item in questions)
    assert "adaptability and 101" not in prompts
    assert "langgraph" in prompts or "rag" in prompts or "retrieval" in prompts
