from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser
from app.core.db import get_db
from app.schemas.interview import LearningPlanOut, SkillGapOut
from app.services import analytics_service

router = APIRouter(tags=["learning"])


@router.get("/skill-gaps", response_model=list[SkillGapOut])
async def skill_gaps(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[SkillGapOut]:
    return await analytics_service.list_gaps(db, user)


@router.get("/learning-plans", response_model=list[LearningPlanOut])
async def learning_plans(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[LearningPlanOut]:
    plans = await analytics_service.list_plans(db, user)
    return [
        LearningPlanOut(
            id=plan.id,
            status=plan.status,
            summary=plan.summary,
            tasks=[
                {
                    "id": task.id,
                    "skill": task.skill,
                    "why_it_matters": task.why_it_matters,
                    "priority": task.priority,
                    "recommended_reading": task.recommended_reading,
                    "search_suggestion": task.search_suggestion,
                    "practice_question": task.practice_question,
                    "coding_exercise": task.coding_exercise,
                    "expected_outcome": task.expected_outcome,
                    "reassessment_criteria": task.reassessment_criteria,
                    "status": task.status,
                }
                for task in plan.tasks
            ],
        )
        for plan in plans
    ]


@router.post("/learning-plans/{plan_id}/reassess", response_model=LearningPlanOut)
async def reassess(
    plan_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> LearningPlanOut:
    plan = await analytics_service.reassess_plan(db, user, plan_id)
    return LearningPlanOut(
        id=plan.id,
        status=plan.status,
        summary=plan.summary,
        tasks=[
            {
                "id": task.id,
                "skill": task.skill,
                "why_it_matters": task.why_it_matters,
                "priority": task.priority,
                "recommended_reading": task.recommended_reading,
                "search_suggestion": task.search_suggestion,
                "practice_question": task.practice_question,
                "coding_exercise": task.coding_exercise,
                "expected_outcome": task.expected_outcome,
                "reassessment_criteria": task.reassessment_criteria,
                "status": task.status,
            }
            for task in plan.tasks
        ],
    )


@router.get("/analytics/progress")
async def analytics(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await analytics_service.progress(db, user)
