from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    service: str


class ReadyResponse(BaseModel):
    status: str
    database: bool
    redis: bool | None = None
    llm_configured: bool


class IdResponse(BaseModel):
    id: UUID


class MessageResponse(BaseModel):
    message: str


class ProvenanceNote(BaseModel):
    kind: str
    detail: str


class Pagination(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
