from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.interview import InterviewPlan, InterviewSession
from app.models.job import JobDescription, JobMatch
from app.models.learning import LearningPlan, SkillGap
from app.models.observability import AuditLog
from app.models.resume import Resume
from app.models.user import User
from app.repositories.audit import write_audit


async def delete_user_data(db: AsyncSession, user: User) -> None:
    settings = get_settings()
    resumes = list(await db.scalars(select(Resume).where(Resume.user_id == user.id)))
    for resume in resumes:
        path = Path(resume.storage_path)
        if path.exists():
            path.unlink()
    media_root = Path(settings.upload_dir) / "media" / str(user.id)
    if media_root.exists():
        for file in media_root.glob("**/*"):
            if file.is_file():
                file.unlink()
    await db.execute(delete(InterviewSession).where(InterviewSession.user_id == user.id))
    await db.execute(delete(InterviewPlan).where(InterviewPlan.user_id == user.id))
    await db.execute(delete(JobMatch).where(JobMatch.user_id == user.id))
    await db.execute(delete(JobDescription).where(JobDescription.user_id == user.id))
    await db.execute(delete(Resume).where(Resume.user_id == user.id))
    await db.execute(delete(LearningPlan).where(LearningPlan.user_id == user.id))
    await db.execute(delete(SkillGap).where(SkillGap.user_id == user.id))
    await write_audit(db, user_id=user.id, action="user.delete_data", resource_type="user", resource_id=str(user.id))
    await db.commit()
