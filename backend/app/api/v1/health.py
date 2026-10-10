from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.schemas.common import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="interviewos-api")


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    settings = get_settings()
    database_ok = False
    redis_ok = None
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
            database_ok = True
    except Exception:
        database_ok = False
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url)
        redis_ok = bool(client.ping())
    except Exception:
        redis_ok = False
    return ReadyResponse(
        status="ok" if database_ok else "degraded",
        database=database_ok,
        redis=redis_ok,
        llm_configured=settings.llm_configured,
    )
