import httpx
import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.services.stt import audio_format, transcribe_audio


def test_audio_format_from_webm():
    assert audio_format("answer.webm", "audio/webm") == "webm"
    assert audio_format("clip.m4a", "audio/mp4") == "m4a"


@pytest.mark.asyncio
async def test_transcribe_audio_reads_free_model():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/audio/transcriptions")
        return httpx.Response(200, json={"text": "I used pandas and SQL"})

    settings = Settings(
        _env_file=None,
        llm_api_key="sk-or-v1-test",
        llm_base_url="https://openrouter.ai/api/v1",
        llm_stt_model="example/whisper:free",
    )
    text = await transcribe_audio(
        b"fake-bytes",
        filename="answer.webm",
        content_type="audio/webm",
        settings=settings,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    assert text == "I used pandas and SQL"


@pytest.mark.asyncio
async def test_transcribe_audio_skips_paid_models():
    settings = Settings(
        _env_file=None,
        llm_api_key="sk-or-v1-test",
        llm_base_url="https://openrouter.ai/api/v1",
        llm_stt_model="openai/whisper-1",
    )
    with pytest.raises(AppError) as exc:
        await transcribe_audio(
            b"fake-bytes",
            filename="answer.wav",
            content_type="audio/wav",
            settings=settings,
        )
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_transcribe_audio_rejects_empty():
    settings = Settings(_env_file=None, llm_api_key="sk-or-v1-test", llm_base_url="https://openrouter.ai/api/v1")
    with pytest.raises(AppError) as exc:
        await transcribe_audio(b"", settings=settings)
    assert exc.value.status_code == 422
