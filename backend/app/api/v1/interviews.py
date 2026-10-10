from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser
from app.core.db import get_db
from app.models.vision import VisualFeatureSummary
from app.schemas.interview import (
    AnswerSubmit,
    ChallengeRequest,
    InterviewPlanCreate,
    InterviewPlanOut,
    SessionCreate,
    SessionOut,
    VisualIngest,
)
from app.services import interview_service
from sqlalchemy import select

router = APIRouter(tags=["interviews"])


@router.post("/interview-plans", response_model=InterviewPlanOut)
async def create_plan(
    payload: InterviewPlanCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> InterviewPlanOut:
    return await interview_service.create_plan(db, user, payload)


@router.post("/interview-sessions", response_model=SessionOut)
async def create_session(
    payload: SessionCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> SessionOut:
    session = await interview_service.start_session(
        db, user, payload.plan_id, payload.visual_consent, payload.speech_assisted
    )
    return SessionOut(**interview_service.session_payload(session))


@router.get("/interview-sessions", response_model=list[SessionOut])
async def list_sessions(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[SessionOut]:
    sessions = await interview_service.list_sessions(db, user)
    return [SessionOut(**interview_service.session_payload(session)) for session in sessions]


@router.get("/interview-sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> SessionOut:
    session = await interview_service.get_session(db, user, session_id)
    return SessionOut(**interview_service.session_payload(session))


@router.post("/interview-sessions/{session_id}/answers")
async def submit_answer(
    session_id: UUID, payload: AnswerSubmit, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await interview_service.submit_answer(db, user, session_id, payload)


@router.post("/interview-sessions/{session_id}/next-question", response_model=SessionOut)
async def next_question(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> SessionOut:
    return SessionOut(**await interview_service.next_question(db, user, session_id))


@router.post("/interview-sessions/{session_id}/pause", response_model=SessionOut)
async def pause_session(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> SessionOut:
    return SessionOut(**await interview_service.pause_or_resume(db, user, session_id, "pause"))


@router.post("/interview-sessions/{session_id}/resume", response_model=SessionOut)
async def resume_session(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> SessionOut:
    return SessionOut(**await interview_service.pause_or_resume(db, user, session_id, "resume"))


@router.post("/interview-sessions/{session_id}/complete")
async def complete_session(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await interview_service.complete_session(db, user, session_id)


@router.get("/interview-sessions/{session_id}/report")
async def get_report(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await interview_service.get_report(db, user, session_id)


@router.get("/interview-sessions/{session_id}/visual-feedback")
async def visual_feedback(session_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    session = await interview_service.get_session(db, user, session_id)
    rows = list(
        await db.scalars(select(VisualFeatureSummary).where(VisualFeatureSummary.session_id == session.id))
    )
    return {
        "session_id": str(session.id),
        "consent": session.visual_consent,
        "features": [
            {
                "feature_type": row.feature_type,
                "value": row.value,
                "usable_frames": row.usable_frames,
                "processing_status": row.processing_status,
                "algorithm_version": row.algorithm_version,
                "quality_indicators": row.quality_indicators,
                "notes": row.notes,
            }
            for row in rows
        ],
        "limitations": [
            "These are descriptive presentation metrics. They do not diagnose emotion, honesty, or confidence."
        ],
    }


@router.post("/interview-sessions/{session_id}/visual-feedback")
async def ingest_visual(
    session_id: UUID, payload: VisualIngest, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    session = await interview_service.get_session(db, user, session_id)
    if not payload.consent or not session.visual_consent:
        return {"accepted": False, "reason": "Visual analysis requires explicit session consent."}
    from app.vision.pipeline import aggregate_observations, analyze_frame
    import base64
    import numpy as np
    import cv2

    observations = []
    for frame in payload.frames[:40]:
        encoded = frame.get("image_b64")
        if not encoded:
            continue
        raw = base64.b64decode(encoded)
        array = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        observations.append(analyze_frame(image, float(frame.get("timestamp_s") or 0)))
    summary = aggregate_observations(observations) if observations else None
    features = payload.aggregated_features or (summary["features"] if summary else [])
    for feature in features:
        db.add(
            VisualFeatureSummary(
                session_id=session.id,
                question_id=payload.question_id,
                feature_type=feature.get("feature_type", "unknown"),
                value=feature.get("value"),
                usable_frames=feature.get("usable_frames") or 0,
                quality_indicators=feature.get("quality_indicators") or {},
                algorithm_version=feature.get("algorithm_version") or "opencv-haar-v1",
                processing_status=feature.get("processing_status") or "ok",
            )
        )
    await db.commit()
    return {"accepted": True, "summary": summary}


@router.post("/interview-sessions/{session_id}/answers/{answer_id}/challenge")
async def challenge(
    session_id: UUID,
    answer_id: UUID,
    payload: ChallengeRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await interview_service.challenge_feedback(db, user, session_id, answer_id, payload.note)
    return {"status": "recorded"}
