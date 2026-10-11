from fastapi import APIRouter, UploadFile

from app.api.v1.deps import CurrentUser
from app.core.errors import AppError
from app.services.stt import transcribe_audio

router = APIRouter(tags=["speech"])


@router.post("/stt")
async def transcribe(file: UploadFile, user: CurrentUser) -> dict[str, str]:
    del user
    data = await file.read()
    if not data:
        raise AppError(422, "validation_error", "No audio was captured")
    text = await transcribe_audio(data, filename=file.filename, content_type=file.content_type)
    return {"text": text}
