from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observability import AuditLog


async def write_audit(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_metadata=metadata or {},
        )
    )
