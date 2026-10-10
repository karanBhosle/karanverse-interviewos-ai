from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.v1.deps import CurrentUser
from app.services.tts import synthesize

router = APIRouter(tags=["speech"])


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: str | None = Field(default=None, max_length=80)


@router.post("/tts")
async def speak(payload: SpeakRequest, user: CurrentUser) -> Response:
    del user
    audio, content_type, voice = await synthesize(payload.text, payload.voice)
    return Response(
        content=audio,
        media_type=content_type,
        headers={
            "Cache-Control": "no-store",
            "X-InterviewOS-Voice": voice,
            "X-InterviewOS-Voice-Style": "indian-english-neural",
        },
    )
