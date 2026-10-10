from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interview import InterviewAnswer, InterviewSession
from app.models.learning import LearningPlan, LearningTask, SkillGap
from app.models.user import User


async def progress(db: AsyncSession, user: User) -> dict:
    sessions = list(
        await db.scalars(
            select(InterviewSession)
            .options(selectinload(InterviewSession.answers).selectinload(InterviewAnswer.evaluation))
            .where(InterviewSession.user_id == user.id)
            .order_by(InterviewSession.created_at.asc())
        )
    )
    points = []
    for session in sessions:
        scores = [
            answer.evaluation.weighted_score
            for answer in session.answers
            if answer.evaluation
        ]
        points.append(
            {
                "session_id": str(session.id),
                "created_at": session.created_at.isoformat(),
                "mode": session.mode,
                "difficulty": session.difficulty,
                "status": session.status,
                "mean_score": round(sum(scores) / len(scores), 2) if scores else None,
                "rubric_version": "v1",
                "comparable_warning": "Compare only sessions that share mode, difficulty, and rubric version.",
            }
        )
    gaps = list(await db.scalars(select(SkillGap).where(SkillGap.user_id == user.id)))
    by_status = defaultdict(int)
    for gap in gaps:
        by_status[gap.status] += 1
    return {
        "sessions": points,
        "gap_status": dict(by_status),
        "completed_sessions": sum(1 for session in sessions if session.status == "complete"),
        "limitations": [
            "Score trends across unlike interview types are not directly comparable.",
        ],
    }


async def list_gaps(db: AsyncSession, user: User) -> list[SkillGap]:
    result = await db.scalars(
        select(SkillGap).where(SkillGap.user_id == user.id).order_by(SkillGap.updated_at.desc())
    )
    return list(result)


async def list_plans(db: AsyncSession, user: User) -> list[LearningPlan]:
    result = await db.scalars(
        select(LearningPlan)
        .options(selectinload(LearningPlan.tasks))
        .where(LearningPlan.user_id == user.id)
        .order_by(LearningPlan.created_at.desc())
    )
    return list(result)


async def reassess_plan(db: AsyncSession, user: User, plan_id, skill: str | None = None) -> LearningPlan:
    from uuid import UUID

    from app.core.errors import NotFoundError
    from app.core.security import assert_owner

    plan = await db.scalar(
        select(LearningPlan).options(selectinload(LearningPlan.tasks)).where(LearningPlan.id == plan_id)
    )
    if plan is None:
        raise NotFoundError("Learning plan not found")
    assert_owner(plan.user_id, user)
    for task in plan.tasks:
        if skill is None or task.skill == skill:
            task.status = "reassessed"
            if task.skill_gap_id:
                gap = await db.scalar(select(SkillGap).where(SkillGap.id == task.skill_gap_id))
                if gap:
                    gap.status = "reassessed"
    await db.commit()
    return plan
