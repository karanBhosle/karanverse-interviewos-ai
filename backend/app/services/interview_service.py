from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationAppError
from app.core.security import assert_owner
from app.evaluation.scoring import filler_word_count
from app.interview.bank import get_question
from app.interview.graph import InterviewGraph
from app.interview.planner import plan_interview
from app.interview.state import InterviewGraphState
from app.learning.planner import plan_from_gaps
from app.models.interview import (
    AnswerEvaluation,
    InterviewAnswer,
    InterviewPlan,
    InterviewQuestion,
    InterviewSession,
)
from app.models.job import JobMatch
from app.models.learning import LearningPlan, LearningTask, SkillGap
from app.models.resume import ResumeVersion
from app.models.user import User
from app.models.vision import VisualFeatureSummary
from app.repositories.audit import write_audit
from app.services.resume_service import get_job, get_resume
from app.vision.pipeline import presentation_checklist

graph_singleton = InterviewGraph()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _question_out(question: InterviewQuestion | None, *, reveal_reference: bool = False):
    if question is None:
        return None
    from app.schemas.interview import QuestionOut

    return QuestionOut(
        id=question.id,
        question_key=question.question_key,
        topic=question.topic,
        difficulty=question.difficulty,
        prompt=question.prompt,
        learning_objective=question.learning_objective,
        sequence=question.sequence,
        hints_available=bool(question.hints),
        help_revealed=question.help_revealed,
        is_follow_up=question.follow_up_of_id is not None,
        reference_guidance=question.reference_guidance if reveal_reference or question.help_revealed else None,
    )


async def create_plan(db: AsyncSession, user: User, payload) -> InterviewPlan:
    resume_version_id = None
    resume_skills: list[str] = []
    missing: list[str] = []
    if payload.resume_id:
        _, version = await get_resume(db, user, payload.resume_id)
        if version:
            resume_version_id = version.id
            resume_skills = list((version.structured_json or {}).get("technologies") or [])
    if payload.job_id:
        await get_job(db, user, payload.job_id)
        match = await db.scalar(
            select(JobMatch)
            .options(selectinload(JobMatch.items))
            .where(JobMatch.user_id == user.id, JobMatch.job_id == payload.job_id)
            .order_by(JobMatch.created_at.desc())
        )
        if match:
            missing = [item.skill for item in match.items if item.matching_status == "missing"]
    prior_gaps = [
        gap.skill
        for gap in await db.scalars(
            select(SkillGap).where(SkillGap.user_id == user.id, SkillGap.status != "reassessed")
        )
    ]
    planned = plan_interview(
        mode=payload.mode,
        difficulty=payload.difficulty,
        duration_minutes=payload.duration_minutes,
        target_role=payload.target_role,
        seniority=payload.seniority,
        resume_skills=resume_skills,
        missing_requirements=missing,
        prior_gaps=prior_gaps,
    )
    plan = InterviewPlan(
        user_id=user.id,
        resume_version_id=resume_version_id,
        job_id=payload.job_id,
        target_role=payload.target_role,
        seniority=payload.seniority,
        mode=payload.mode,
        difficulty=payload.difficulty,
        duration_minutes=payload.duration_minutes,
        webcam_assisted=payload.webcam_assisted,
        planned_questions=planned["planned_questions"],
        planner_notes=planned["planner_notes"],
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def start_session(db: AsyncSession, user: User, plan_id: UUID, visual_consent: bool) -> InterviewSession:
    plan = await db.scalar(select(InterviewPlan).where(InterviewPlan.id == plan_id))
    if plan is None:
        raise NotFoundError("Interview plan not found")
    assert_owner(plan.user_id, user)
    settings = get_settings()
    resume_summary = {}
    if plan.resume_version_id:
        version = await db.scalar(select(ResumeVersion).where(ResumeVersion.id == plan.resume_version_id))
        if version:
            resume_summary = version.structured_json or {}
    state = InterviewGraphState(
        session_id="pending",
        user_id=str(user.id),
        mode=plan.mode,
        difficulty=plan.difficulty,
        duration_minutes=plan.duration_minutes,
        target_role=plan.target_role,
        seniority=plan.seniority,
        resume_summary=resume_summary,
        prior_gaps=[item["topic"] for item in plan.planned_questions],
        planned_question_keys=[item["question_key"] for item in plan.planned_questions],
        uncovered_competencies=[item["topic"] for item in plan.planned_questions],
        max_questions=max(3, len(plan.planned_questions)),
        max_llm_calls=settings.session_max_llm_calls,
        max_tokens=settings.session_max_tokens,
        provider_available=settings.llm_configured,
    )
    state = graph_singleton.invoke(state)
    session = InterviewSession(
        user_id=user.id,
        plan_id=plan.id,
        status="active",
        mode=plan.mode,
        difficulty=plan.difficulty,
        duration_minutes=plan.duration_minutes,
        webcam_assisted=plan.webcam_assisted,
        visual_consent=visual_consent and plan.webcam_assisted,
        started_at=_utcnow(),
        covered_competencies=state.covered_competencies,
        uncovered_competencies=state.uncovered_competencies,
        asked_question_keys=state.asked_question_keys,
        graph_state=state.model_dump(),
        provider_available=settings.llm_configured,
    )
    db.add(session)
    await db.flush()
    if state.current_question:
        await _persist_question(db, session, state.current_question, sequence=1)
    state.session_id = str(session.id)
    session.graph_state = state.model_dump()
    await db.commit()
    return await get_session(db, user, session.id)


async def _persist_question(
    db: AsyncSession, session: InterviewSession, question: dict, sequence: int, parent_id: UUID | None = None
) -> InterviewQuestion:
    bank = get_question(question["question_key"]) or question
    row = InterviewQuestion(
        session_id=session.id,
        question_key=question["question_key"],
        topic=question.get("topic", "general"),
        difficulty=question.get("difficulty", session.difficulty),
        prompt=question["prompt"],
        learning_objective=question.get("learning_objective", ""),
        expected_concepts=question.get("expected_concepts") or bank.get("expected_concepts") or [],
        rubric_version="v1",
        follow_up_of_id=parent_id,
        sequence=sequence,
        reference_guidance=question.get("reference_guidance") or bank.get("reference_guidance") or "",
        hints=question.get("hints") or bank.get("hints") or [],
        started_at=_utcnow(),
    )
    db.add(row)
    await db.flush()
    return row


async def get_session(db: AsyncSession, user: User, session_id: UUID) -> InterviewSession:
    session = await db.scalar(
        select(InterviewSession)
        .options(selectinload(InterviewSession.questions), selectinload(InterviewSession.answers))
        .where(InterviewSession.id == session_id)
    )
    if session is None:
        raise NotFoundError("Interview session not found")
    assert_owner(session.user_id, user)
    return session


async def list_sessions(db: AsyncSession, user: User) -> list[InterviewSession]:
    result = await db.scalars(
        select(InterviewSession)
        .options(selectinload(InterviewSession.questions), selectinload(InterviewSession.answers))
        .where(InterviewSession.user_id == user.id)
        .order_by(InterviewSession.created_at.desc())
    )
    return list(result)


def current_question(session: InterviewSession) -> InterviewQuestion | None:
    unanswered_ids = {answer.question_id for answer in session.answers}
    open_questions = [q for q in session.questions if q.id not in unanswered_ids]
    if not open_questions:
        return None
    return max(open_questions, key=lambda item: item.sequence)


def session_payload(session: InterviewSession) -> dict:
    question = current_question(session)
    return {
        "id": session.id,
        "status": session.status,
        "mode": session.mode,
        "difficulty": session.difficulty,
        "duration_minutes": session.duration_minutes,
        "webcam_assisted": session.webcam_assisted,
        "visual_consent": session.visual_consent,
        "covered_competencies": session.covered_competencies,
        "uncovered_competencies": session.uncovered_competencies,
        "follow_up_count": session.follow_up_count,
        "provider_available": session.provider_available,
        "current_question": _question_out(question),
    }


async def submit_answer(db: AsyncSession, user: User, session_id: UUID, payload) -> dict:
    session = await get_session(db, user, session_id)
    if session.status not in {"active", "paused"}:
        raise ValidationAppError("This session is no longer accepting answers")
    question = next((q for q in session.questions if q.id == payload.question_id), None)
    if question is None:
        raise NotFoundError("Question not found in this session")
    if payload.request_help:
        question.help_revealed = True
    answer = InterviewAnswer(
        session_id=session.id,
        question_id=question.id,
        raw_text=payload.raw_text,
        started_at=payload.started_at or question.started_at,
        ended_at=payload.ended_at or _utcnow(),
        duration_seconds=payload.duration_seconds,
        transcript_text=payload.raw_text,
        transcript_provenance="typed",
        filler_word_count=filler_word_count(payload.raw_text),
    )
    question.ended_at = answer.ended_at
    db.add(answer)
    await db.flush()

    state = InterviewGraphState.model_validate(session.graph_state)
    state.session_id = str(session.id)
    state.current_question = {
        "question_key": question.question_key,
        "topic": question.topic,
        "difficulty": question.difficulty,
        "prompt": question.prompt,
        "learning_objective": question.learning_objective,
        "expected_concepts": question.expected_concepts,
        "hints": question.hints,
        "reference_guidance": question.reference_guidance,
        "rubric_type": (get_question(question.question_key) or {}).get("rubric_type", "technical"),
    }
    state.current_answer = payload.raw_text
    state.status = "evaluating"
    state.asked_question_keys = list(session.asked_question_keys)
    state = graph_singleton.answer_context_builder(state)
    state = graph_singleton.evidence_retriever(state)
    state = graph_singleton.answer_evaluator(state)
    evaluation = state.last_evaluation or {}
    payload_data = evaluation.get("payload") or {}
    db.add(
        AnswerEvaluation(
            answer_id=answer.id,
            rubric_version=question.rubric_version,
            dimension_scores=payload_data.get("dimensions") or [],
            evidence_excerpts=[
                item.get("answer_excerpt")
                for item in (payload_data.get("dimensions") or [])
                if item.get("answer_excerpt")
            ],
            missing_concepts=payload_data.get("missing_concepts") or [],
            incorrect_claims=payload_data.get("incorrect_claims") or [],
            feedback=payload_data.get("feedback") or "",
            suggested_stronger_answer=payload_data.get("suggested_stronger_answer") or "",
            follow_up_recommendation=payload_data.get("follow_up_recommendation") or "next_competency",
            evaluation_model=evaluation.get("evaluation_model"),
            evaluation_version="v1",
            provenance=evaluation.get("provenance") or "deterministic_concept_coverage",
            weighted_score=evaluation.get("weighted_score") or 0,
            llm_raw_valid=bool(evaluation.get("llm_raw_valid")),
        )
    )
    if payload.visual_features and session.visual_consent:
        for feature in payload.visual_features:
            db.add(
                VisualFeatureSummary(
                    session_id=session.id,
                    question_id=question.id,
                    feature_type=feature.get("feature_type", "unknown"),
                    value=feature.get("value"),
                    usable_frames=feature.get("usable_frames") or 0,
                    quality_indicators=feature.get("quality_indicators") or {},
                    algorithm_version=feature.get("algorithm_version") or "client-v1",
                    processing_status=feature.get("processing_status") or "ok",
                    notes=feature.get("notes"),
                )
            )
    state = graph_singleton.follow_up_decision(state)
    if state.status == "follow_up" and state.current_question:
        parent_id = question.id
        await _persist_question(
            db, session, state.current_question, sequence=len(session.questions) + 1, parent_id=parent_id
        )
        session.follow_up_count = state.follow_up_count
    elif state.current_question is None:
        next_state = graph_singleton.question_generator(state)
        if next_state.current_question:
            await _persist_question(db, session, next_state.current_question, sequence=len(session.questions) + 1)
            state = next_state
        else:
            state = next_state
    session.asked_question_keys = state.asked_question_keys
    session.covered_competencies = state.covered_competencies
    session.uncovered_competencies = state.uncovered_competencies
    session.llm_calls_used = state.llm_calls_used
    session.tokens_used = state.tokens_used
    session.graph_state = state.model_dump()
    session.provider_available = state.provider_available
    await db.commit()
    session = await get_session(db, user, session.id)
    evaluation_out = _evaluation_out(evaluation, question)
    return {"session": session_payload(session), "evaluation": evaluation_out}


def _evaluation_out(evaluation: dict, question: InterviewQuestion) -> dict:
    payload = evaluation.get("payload") or {}
    return {
        "weighted_score": evaluation.get("weighted_score") or 0,
        "provenance": evaluation.get("provenance") or "deterministic_concept_coverage",
        "evaluation_model": evaluation.get("evaluation_model"),
        "rubric_version": question.rubric_version,
        "dimension_scores": payload.get("dimensions") or [],
        "evidence_excerpts": [
            item.get("answer_excerpt") for item in (payload.get("dimensions") or []) if item.get("answer_excerpt")
        ],
        "missing_concepts": payload.get("missing_concepts") or [],
        "incorrect_claims": payload.get("incorrect_claims") or [],
        "feedback": payload.get("feedback") or "",
        "suggested_stronger_answer": payload.get("suggested_stronger_answer") or "",
        "follow_up_recommendation": payload.get("follow_up_recommendation") or "next_competency",
        "limitations": [
            "This score is a coaching signal, not an objective measure of job performance.",
            "Final weights were computed in Python after validating component scores.",
        ],
    }


async def next_question(db: AsyncSession, user: User, session_id: UUID) -> dict:
    session = await get_session(db, user, session_id)
    existing = current_question(session)
    if existing:
        return session_payload(session)
    state = InterviewGraphState.model_validate(session.graph_state)
    state = graph_singleton.question_generator(state)
    if state.current_question:
        await _persist_question(db, session, state.current_question, sequence=len(session.questions) + 1)
    session.graph_state = state.model_dump()
    session.status = "active" if state.current_question else session.status
    await db.commit()
    session = await get_session(db, user, session.id)
    return session_payload(session)


async def pause_or_resume(db: AsyncSession, user: User, session_id: UUID, action: str) -> dict:
    session = await get_session(db, user, session_id)
    if action == "pause":
        session.status = "paused"
        session.paused_at = _utcnow()
    elif action == "resume":
        session.status = "active"
        session.paused_at = None
    await db.commit()
    return session_payload(session)


async def complete_session(db: AsyncSession, user: User, session_id: UUID) -> dict:
    session = await get_session(db, user, session_id)
    state = InterviewGraphState.model_validate(session.graph_state)
    state.status = "aggregating"
    state = graph_singleton.skill_gap_analyzer(state)
    state = graph_singleton.learning_plan_generator(state)
    state = graph_singleton.report_validator(state)
    evaluations = await _session_evaluations(db, session)
    report = await _build_report(db, user, session, state, evaluations)
    session.report_json = report
    session.status = "complete"
    session.completed_at = _utcnow()
    session.graph_state = state.model_dump()
    await _persist_gaps_and_plan(db, user, session, state)
    await write_audit(db, user_id=user.id, action="session.complete", resource_type="session", resource_id=str(session.id))
    await db.commit()
    return report


async def _session_evaluations(db: AsyncSession, session: InterviewSession) -> list[AnswerEvaluation]:
    answers = await db.scalars(
        select(InterviewAnswer)
        .options(selectinload(InterviewAnswer.evaluation))
        .where(InterviewAnswer.session_id == session.id)
    )
    return [answer.evaluation for answer in answers if answer.evaluation]


async def _build_report(
    db: AsyncSession,
    user: User,
    session: InterviewSession,
    state: InterviewGraphState,
    evaluations: list[AnswerEvaluation],
) -> dict:
    scores = [item.weighted_score for item in evaluations]
    technical = round(sum(scores) / len(scores), 2) if scores else None
    visual_rows = list(
        await db.scalars(select(VisualFeatureSummary).where(VisualFeatureSummary.session_id == session.id))
    )
    visual_features = [
        {
            "feature_type": row.feature_type,
            "value": row.value,
            "usable_frames": row.usable_frames,
            "processing_status": row.processing_status,
            "algorithm_version": row.algorithm_version,
            "quality_indicators": row.quality_indicators,
        }
        for row in visual_rows
    ]
    checklist = presentation_checklist(visual_features, user.visual_checklist_enabled) if visual_features else None
    competency: dict[str, list[float]] = {}
    for question in session.questions:
        eval_row = next((item for item in evaluations if item.answer and False), None)
        del eval_row
    answer_map = {answer.question_id: answer for answer in session.answers}
    for question in session.questions:
        answer = answer_map.get(question.id)
        if answer and answer.evaluation:
            competency.setdefault(question.topic, []).append(answer.evaluation.weighted_score)
    competency_scores = {
        topic: round(sum(values) / len(values), 2) for topic, values in competency.items() if values
    }
    return {
        "session_id": str(session.id),
        "status": "complete",
        "technical_answer_score": technical,
        "score_provenance": evaluations[0].provenance if evaluations else None,
        "topic_coverage": {
            "covered": session.covered_competencies,
            "uncovered": session.uncovered_competencies,
            "competency_scores": competency_scores,
        },
        "communication_feedback": [
            {
                "question_id": str(answer.question_id),
                "filler_word_count": answer.filler_word_count,
                "duration_seconds": answer.duration_seconds,
                "note": "Filler counts and duration are descriptive. They are not proof of nervousness.",
            }
            for answer in session.answers
        ],
        "resume_job_alignment": state.job_alignment,
        "visual_observations": visual_features,
        "presentation_checklist": checklist,
        "recording_quality": [item for item in visual_features if "blur" in item["feature_type"] or "dark" in item["feature_type"] or item["feature_type"].endswith("quality")],
        "unresolved_gaps": state.skill_gaps,
        "answers": [
            {
                "question": question.prompt,
                "topic": question.topic,
                "answer": next((a.raw_text for a in session.answers if a.question_id == question.id), None),
                "evaluation": (
                    _evaluation_out(
                        {
                            "weighted_score": answer_map[question.id].evaluation.weighted_score,
                            "provenance": answer_map[question.id].evaluation.provenance,
                            "evaluation_model": answer_map[question.id].evaluation.evaluation_model,
                            "payload": {
                                "dimensions": answer_map[question.id].evaluation.dimension_scores,
                                "missing_concepts": answer_map[question.id].evaluation.missing_concepts,
                                "incorrect_claims": answer_map[question.id].evaluation.incorrect_claims,
                                "feedback": answer_map[question.id].evaluation.feedback,
                                "suggested_stronger_answer": answer_map[question.id].evaluation.suggested_stronger_answer,
                                "follow_up_recommendation": answer_map[question.id].evaluation.follow_up_recommendation,
                            },
                        },
                        question,
                    )
                    if question.id in answer_map and answer_map[question.id].evaluation
                    else None
                ),
            }
            for question in sorted(session.questions, key=lambda item: item.sequence)
        ],
        "learning_plan": state.learning_plan,
        "limitations": [
            "Scores are coaching signals, not hiring predictions.",
            "Visual metrics are optional descriptive observations with quality flags.",
            "Sessions with different difficulty or rubric versions are not directly comparable.",
        ],
        "provider_available": session.provider_available,
        "errors": state.errors,
    }


async def _persist_gaps_and_plan(
    db: AsyncSession, user: User, session: InterviewSession, state: InterviewGraphState
) -> None:
    created_gaps: list[SkillGap] = []
    for gap in state.skill_gaps:
        existing = await db.scalar(
            select(SkillGap).where(
                SkillGap.user_id == user.id, SkillGap.skill == gap["skill"], SkillGap.status != "reassessed"
            )
        )
        if existing:
            existing.recurrence += 1
            existing.evidence = gap["evidence"]
            existing.session_id = session.id
            created_gaps.append(existing)
            continue
        row = SkillGap(
            user_id=user.id,
            session_id=session.id,
            skill=gap["skill"],
            evidence=gap["evidence"],
            why_it_matters=f"Relevant to a {state.target_role} interview.",
            severity=gap.get("severity", "medium"),
            job_relevance=gap.get("job_relevance", "medium"),
        )
        db.add(row)
        created_gaps.append(row)
    await db.flush()
    plan_data = state.learning_plan or plan_from_gaps(state.skill_gaps, target_role=state.target_role)
    plan = LearningPlan(user_id=user.id, session_id=session.id, summary=plan_data.get("summary", ""), status="active")
    db.add(plan)
    await db.flush()
    gap_by_skill = {row.skill: row for row in created_gaps}
    for task in plan_data.get("tasks", []):
        gap = gap_by_skill.get(task["skill"])
        db.add(
            LearningTask(
                plan_id=plan.id,
                skill_gap_id=gap.id if gap else None,
                skill=task["skill"],
                why_it_matters=task["why_it_matters"],
                priority=task["priority"],
                recommended_reading=task.get("recommended_reading"),
                search_suggestion=task.get("search_suggestion"),
                practice_question=task["practice_question"],
                coding_exercise=task.get("coding_exercise"),
                expected_outcome=task["expected_outcome"],
                reassessment_criteria=task["reassessment_criteria"],
            )
        )


async def get_report(db: AsyncSession, user: User, session_id: UUID) -> dict:
    session = await get_session(db, user, session_id)
    if session.report_json:
        return session.report_json
    if session.status != "complete":
        raise ValidationAppError("Complete the session to generate a saved report")
    return session.report_json or {}


async def challenge_feedback(db: AsyncSession, user: User, session_id: UUID, answer_id: UUID, note: str) -> None:
    session = await get_session(db, user, session_id)
    answer = next((item for item in session.answers if item.id == answer_id), None)
    if answer is None:
        raise NotFoundError("Answer not found")
    answer.challenged = True
    answer.challenge_note = note
    await write_audit(
        db,
        user_id=user.id,
        action="evaluation.challenge",
        resource_type="answer",
        resource_id=str(answer_id),
        metadata={"note": note[:200]},
    )
    await db.commit()
