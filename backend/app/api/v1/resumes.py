from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser
from app.core.db import get_db
from app.schemas.common import MessageResponse
from app.schemas.resume import JobCreate, JobDetail, JobMatchOut, JobMatchRequest, ResumeDetail, ResumeSummary
from app.services import resume_service

router = APIRouter(tags=["resumes"])


@router.post("/resumes", response_model=ResumeSummary)
async def upload_resume(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> ResumeSummary:
    data = await file.read()
    resume = await resume_service.save_resume(db, user, file.filename or "resume.pdf", file.content_type or "", data)
    return resume


@router.get("/resumes", response_model=list[ResumeSummary])
async def list_resumes(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[ResumeSummary]:
    return await resume_service.list_resumes(db, user)


@router.get("/resumes/{resume_id}", response_model=ResumeDetail)
async def get_resume(resume_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> ResumeDetail:
    resume, version = await resume_service.get_resume(db, user, resume_id)
    structured = (version.structured_json if version else None) or {}
    return ResumeDetail(
        id=resume.id,
        original_filename=resume.original_filename,
        content_type=resume.content_type,
        size_bytes=resume.size_bytes,
        status=resume.status,
        latest_version_id=version.id if version else None,
        structured=structured,
        extracted_text=version.extracted_text if version else None,
        warnings=list(structured.get("warnings") or []),
    )


@router.delete("/resumes/{resume_id}", response_model=MessageResponse)
async def delete_resume(resume_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    await resume_service.delete_resume(db, user, resume_id)
    return MessageResponse(message="Resume deleted")


@router.post("/jobs", response_model=JobDetail)
async def create_job(payload: JobCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> JobDetail:
    return await resume_service.create_job(db, user, payload)


@router.get("/jobs", response_model=list[JobDetail])
async def list_jobs(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[JobDetail]:
    return await resume_service.list_jobs(db, user)


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def get_job(job_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> JobDetail:
    return await resume_service.get_job(db, user, job_id)


@router.post("/job-matches", response_model=JobMatchOut)
async def create_match(payload: JobMatchRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> JobMatchOut:
    match, items = await resume_service.create_match(db, user, payload.resume_id, payload.job_id)
    return JobMatchOut(
        id=match.id,
        alignment_score=match.alignment_score,
        score_explanation=match.score_explanation,
        strong_count=match.strong_count,
        partial_count=match.partial_count,
        missing_count=match.missing_count,
        items=items,
        questions_prepared=bool(match.prepared_questions),
    )
