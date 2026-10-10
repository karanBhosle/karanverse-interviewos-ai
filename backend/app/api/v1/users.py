from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser
from app.core.db import get_db
from app.schemas.common import MessageResponse
from app.services.privacy_service import delete_user_data

router = APIRouter(tags=["users"])


@router.delete("/users/me/data", response_model=MessageResponse)
async def delete_my_data(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    await delete_user_data(db, user)
    return MessageResponse(message="Resumes, sessions, media, and derived indexes for this account were deleted.")
