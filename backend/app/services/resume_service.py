from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationAppError
from app.core.security import assert_owner
from app.interview.question_gen import generate_resume_jd_questions
from app.job_matching.extractor import extract_requirements
from app.job_matching.matcher import match_requirements
from app.models.job import JobDescription, JobMatch, JobMatchItem, JobRequirement
from app.models.resume import CandidateSkillEvidence, Resume, ResumeVersion
from app.models.user import User
from app.repositories.audit import write_audit
from app.resume.extractor import structure_resume
from app.resume.parser import extract_text, sniff_kind


async def save_resume(db: AsyncSession, user: User, filename: str, content_type: str, data: bytes) -> Resume:
    settings = get_settings()
    if len(data) > settings.upload_limit_bytes:
        raise ValidationAppError(f"File exceeds the {settings.upload_limit_mb} MB upload limit")
    kind = sniff_kind(filename, content_type)
    extracted = extract_text(data, kind, enable_ocr=False)
    if not extracted.text.strip():
        raise ValidationAppError(
            "No text could be extracted. If this is a scanned PDF, enable OCR locally or upload a text-based file."
        )
    structured = structure_resume(extracted)
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{user.id}_{uuid4().hex}_{Path(filename).name}"
    path = upload_dir / stored_name
    path.write_bytes(data)
    resume = Resume(
        user_id=user.id,
        original_filename=filename,
        content_type=content_type or f"application/{kind}",
        size_bytes=len(data),
        storage_path=str(path),
        status="processed",
    )
    db.add(resume)
    await db.flush()
    version = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        extracted_text=extracted.text,
        structured_json=structured,
        extraction_method=extracted.method,
        ocr_used=extracted.ocr_used,
    )
    db.add(version)
    await db.flush()
    for skill in structured["skills"]:
        db.add(
            CandidateSkillEvidence(
                resume_version_id=version.id,
                skill_raw=skill["skill_raw"],
                skill_normalized=skill["skill_normalized"],
                evidence_text=skill["evidence_text"],
                source_section=skill["source_section"],
                source_page=skill.get("source_page"),
                evidence_kind=skill["evidence_kind"],
            )
        )
    await write_audit(db, user_id=user.id, action="resume.upload", resource_type="resume", resource_id=str(resume.id))
    await db.commit()
    await db.refresh(resume)
    return resume


async def list_resumes(db: AsyncSession, user: User) -> list[Resume]:
    result = await db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()))
    return list(result)


async def get_resume(db: AsyncSession, user: User, resume_id: UUID) -> tuple[Resume, ResumeVersion | None]:
    resume = await db.scalar(select(Resume).where(Resume.id == resume_id))
    if resume is None:
        raise NotFoundError("Resume not found")
    assert_owner(resume.user_id, user)
    version = await db.scalar(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume.id)
        .order_by(ResumeVersion.version_number.desc())
    )
    return resume, version


async def delete_resume(db: AsyncSession, user: User, resume_id: UUID) -> None:
    resume, _ = await get_resume(db, user, resume_id)
    path = Path(resume.storage_path)
    if path.exists():
        path.unlink()
    await db.delete(resume)
    await write_audit(db, user_id=user.id, action="resume.delete", resource_type="resume", resource_id=str(resume_id))
    await db.commit()


async def create_job(db: AsyncSession, user: User, payload) -> JobDescription:
    requirements = extract_requirements(payload.raw_text)
    job = JobDescription(
        user_id=user.id,
        title=payload.title,
        company=payload.company,
        seniority=payload.seniority,
        raw_text=payload.raw_text,
        extraction_method="deterministic",
    )
    db.add(job)
    await db.flush()
    for item in requirements:
        db.add(
            JobRequirement(
                job_id=job.id,
                requirement_key=item["requirement_key"],
                skill=item["skill"],
                description=item["description"],
                importance=item["importance"],
                weight=item["weight"],
            )
        )
    await write_audit(db, user_id=user.id, action="job.create", resource_type="job", resource_id=str(job.id))
    await db.commit()
    return await get_job(db, user, job.id)


async def get_job(db: AsyncSession, user: User, job_id: UUID) -> JobDescription:
    job = await db.scalar(
        select(JobDescription).options(selectinload(JobDescription.requirements)).where(JobDescription.id == job_id)
    )
    if job is None:
        raise NotFoundError("Job description not found")
    assert_owner(job.user_id, user)
    return job


async def list_jobs(db: AsyncSession, user: User) -> list[JobDescription]:
    result = await db.scalars(
        select(JobDescription)
        .options(selectinload(JobDescription.requirements))
        .where(JobDescription.user_id == user.id)
        .order_by(JobDescription.created_at.desc())
    )
    return list(result)


async def create_match(db: AsyncSession, user: User, resume_id: UUID, job_id: UUID) -> JobMatch:
    resume, version = await get_resume(db, user, resume_id)
    if version is None:
        raise ValidationAppError("Resume has no extracted version")
    job = await get_job(db, user, job_id)
    evidence = await db.scalars(
        select(CandidateSkillEvidence).where(CandidateSkillEvidence.resume_version_id == version.id)
    )
    requirements = [
        {
            "requirement_key": req.requirement_key,
            "skill": req.skill,
            "description": req.description,
            "importance": req.importance,
            "weight": req.weight,
            "id": req.id,
        }
        for req in job.requirements
    ]
    result = match_requirements(
        requirements,
        [
            {
                "skill_normalized": row.skill_normalized,
                "evidence_text": row.evidence_text,
                "source_section": row.source_section,
                "source_page": row.source_page,
                "evidence_kind": row.evidence_kind,
            }
            for row in evidence
        ],
        resume_summary=version.structured_json,
        resume_text=version.extracted_text,
    )
    job_context = {
        "title": job.title,
        "company": job.company or "",
        "requirements": [
            {
                "skill": item["skill"],
                "description": item["description"],
                "status": item["matching_status"],
            }
            for item in result["items"]
        ],
        "missing": [item["skill"] for item in result["items"] if item["matching_status"] == "missing"],
        "strong": [item["skill"] for item in result["items"] if item["matching_status"] == "strong"],
        "overlap": [item["skill"] for item in result["items"] if item["matching_status"] in {"strong", "partial"}],
    }
    prepared = await generate_resume_jd_questions(
        resume_summary=version.structured_json,
        job_context=job_context,
        mode="mixed",
        difficulty="easy",
        budget=12,
        target_role=job.title or "this role",
        resume_text=version.extracted_text or "",
    )
    match = JobMatch(
        user_id=user.id,
        resume_version_id=version.id,
        job_id=job.id,
        alignment_score=result["alignment_score"],
        score_explanation=result["score_explanation"],
        strong_count=result["strong_count"],
        partial_count=result["partial_count"],
        missing_count=result["missing_count"],
        prepared_questions=prepared,
    )
    db.add(match)
    await db.flush()
    req_by_key = {req.requirement_key: req for req in job.requirements}
    for item in result["items"]:
        requirement = req_by_key[item["requirement_key"]]
        db.add(
            JobMatchItem(
                match_id=match.id,
                requirement_id=requirement.id,
                evidence_found=item["evidence_found"],
                evidence_source=item["evidence_source"],
                evidence_strength=item["evidence_strength"],
                matching_status=item["matching_status"],
                follow_up_questions=item["follow_up_questions"],
            )
        )
    await db.commit()
    loaded = await db.scalar(
        select(JobMatch).options(selectinload(JobMatch.items)).where(JobMatch.id == match.id)
    )
    return loaded, result["items"]
