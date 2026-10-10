from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import get_settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.purge_expired_media")
def purge_expired_media() -> int:
    settings = get_settings()
    if settings.media_storage_enabled:
        root = Path(settings.upload_dir) / "media"
    else:
        root = Path(settings.upload_dir) / "media"
    if not root.exists():
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=settings.media_retention_days)
    removed = 0
    for file in root.glob("**/*"):
        if file.is_file() and datetime.fromtimestamp(file.stat().st_mtime, tz=UTC) < cutoff:
            file.unlink()
            removed += 1
    logger.info("purged %s expired media files", removed)
    return removed


@celery_app.task(name="app.workers.tasks.rebuild_session_report")
def rebuild_session_report(session_id: str) -> str:
    return session_id
