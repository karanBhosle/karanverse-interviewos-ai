from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    display_name: str
    email: str


class UserResponse(ORMModel):
    id: UUID
    email: str
    display_name: str
    resume_retention_enabled: bool
    session_history_enabled: bool
    camera_consent: bool
    media_storage_consent: bool
    visual_checklist_enabled: bool
    visual_analysis_opt_in: bool


class PrivacyUpdate(BaseModel):
    resume_retention_enabled: bool | None = None
    session_history_enabled: bool | None = None
    camera_consent: bool | None = None
    media_storage_consent: bool | None = None
    visual_checklist_enabled: bool | None = None
    visual_analysis_opt_in: bool | None = None
