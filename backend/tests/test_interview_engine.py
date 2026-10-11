from app.evaluation.followups import decide_follow_up, next_unasked_question
from app.evaluation.scoring import (
    DimensionScore,
    ModelEvaluationPayload,
    apply_model_payload,
    deterministic_evaluation,
    weighted_score,
)
from app.interview.bank import get_question, questions_for_mode
from app.interview.graph import InterviewGraph
from app.interview.state import InterviewGraphState


def test_duplicate_question_prevention():
    asked = ["py_mutability"]
    nxt = next_unasked_question("python_coding", asked, ["python"])
    assert nxt is not None
    assert nxt["question_key"] not in asked


def test_follow_up_limits():
    question = get_question("py_mutability")
    evaluation = deterministic_evaluation(question, "I like python lists")
    follow = decide_follow_up(question, evaluation, follow_up_count=2, max_follow_ups=2, asked_keys=[])
    assert follow is None
    follow = decide_follow_up(question, evaluation, follow_up_count=0, max_follow_ups=2, asked_keys=[])
    assert follow is not None
    assert follow["question_key"] not in {"py_mutability"}
    skipped = decide_follow_up(
        question,
        {**evaluation, "skip_follow_up": True},
        follow_up_count=0,
        max_follow_ups=2,
        asked_keys=[],
    )
    assert skipped is None


def test_weighted_score_is_python_computed():
    dimensions = [
        DimensionScore(id="a", label="A", weight=0.5, score=5, justification="ok", answer_excerpt="x"),
        DimensionScore(id="b", label="B", weight=0.5, score=1, justification="ok", answer_excerpt="y"),
    ]
    assert weighted_score(dimensions) == 60.0


def test_schema_rejects_unknown_follow_up():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ModelEvaluationPayload(
            dimensions=[],
            feedback="x",
            suggested_stronger_answer="y",
            follow_up_recommendation="hire_them",
        )


def test_model_payload_must_match_rubric():
    import pytest

    question = get_question("py_mutability")
    payload = ModelEvaluationPayload(
        dimensions=[
            DimensionScore(id="wrong", label="Wrong", weight=1, score=3, justification="no", answer_excerpt="z")
        ],
        feedback="x",
        suggested_stronger_answer="y",
    )
    with pytest.raises(ValueError):
        apply_model_payload(question, payload, model_name="mock")


def test_graph_moves_on_when_user_does_not_know():
    question = get_question("py_mutability")
    evaluation = deterministic_evaluation(question, "I don't know")
    graph = InterviewGraph()
    state = InterviewGraphState(
        session_id="s1",
        user_id="u1",
        mode="python_coding",
        difficulty="easy",
        duration_minutes=20,
        current_question=question,
        current_answer="I don't know",
        last_evaluation={
            "payload": evaluation["payload"].model_dump(),
            **{key: value for key, value in evaluation.items() if key != "payload"},
        },
        max_follow_ups=0,
        asked_question_keys=["py_mutability"],
        max_questions=4,
    )
    state = graph.follow_up_decision(state)
    assert state.status != "follow_up"
    assert state.current_question is None


def test_graph_state_transitions_and_coverage():
    question = get_question("py_mutability")
    graph = InterviewGraph()
    state = InterviewGraphState(
        session_id="s1",
        user_id="u1",
        mode="python_coding",
        difficulty="medium",
        duration_minutes=20,
        planned_question_keys=["py_mutability"],
        uncovered_competencies=["python"],
        current_question={
            "question_key": question["question_key"],
            "topic": question["topic"],
            "difficulty": question["difficulty"],
            "prompt": question["prompt"],
            "learning_objective": question["learning_objective"],
            "expected_concepts": question["expected_concepts"],
            "hints": question["hints"],
            "reference_guidance": question["reference_guidance"],
            "rubric_type": question["rubric_type"],
        },
        current_answer=(
            "Mutable objects such as lists can change in place, which creates aliasing. "
            "Immutable objects such as tuples cannot. Default argument evaluation happens "
            "once at function definition, so a mutable default list is shared. "
            "Object identity is distinct from equality."
        ),
        max_follow_ups=0,
        max_questions=1,
    )
    state = graph.answer_evaluator(state)
    assert "python" in state.covered_competencies
    assert state.last_evaluation["provenance"] == "deterministic_concept_coverage"
    assert 0 <= state.last_evaluation["weighted_score"] <= 100
    state = graph.follow_up_decision(state)
    assert state.status in {"asking", "follow_up"}


def test_mode_coverage_has_questions():
    for mode in (
        "technical_fundamentals",
        "python_coding",
        "machine_learning",
        "genai_llms",
        "rag_hybrid_retrieval",
        "agentic_ai_langgraph",
        "system_design",
        "project_deep_dive",
        "behavioral",
        "mixed",
    ):
        assert questions_for_mode(mode)
