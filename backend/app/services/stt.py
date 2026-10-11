from __future__ import annotations

import base64
import logging

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import AppError, ProviderUnavailableError
from app.core.logging import redact

logger = logging.getLogger(__name__)

def is_free_stt_model(name: str) -> bool:
    return name.strip().lower().endswith(":free")


def audio_format(filename: str | None, content_type: str | None) -> str:
    blob = f"{filename or ''} {content_type or ''}".lower()
    for fmt in ("webm", "wav", "mp3", "ogg", "flac", "aac", "m4a"):
        if fmt in blob:
            return fmt
    if "mp4" in blob:
        return "m4a"
    return "webm"


def _headers(settings: Settings) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    if settings.llm_http_referer:
        headers["HTTP-Referer"] = settings.llm_http_referer
    if settings.llm_app_name:
        headers["X-Title"] = settings.llm_app_name
    return headers


def _models(settings: Settings) -> list[str]:
    name = settings.llm_stt_model.strip()
    if name and is_free_stt_model(name):
        return [name]
    return []


async def transcribe_audio(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> str:
    cfg = settings or get_settings()
    if not data:
        raise AppError(422, "validation_error", "No audio was captured")
    if len(data) > 2_000_000:
        raise AppError(413, "payload_too_large", "The spoken clip is too long to transcribe")

    models = _models(cfg)
    if not models:
        raise AppError(
            503,
            "stt_unavailable",
            "No free speech-to-text model is configured. InterviewOS transcribes on this device.",
        )
    if not cfg.llm_api_key.strip() or not cfg.llm_base_url.strip():
        raise ProviderUnavailableError("Speech-to-text needs LLM_API_KEY and LLM_BASE_URL")

    fmt = audio_format(filename, content_type)
    payload = {
        "input_audio": {"data": base64.b64encode(data).decode("ascii"), "format": fmt},
        "language": "en",
    }
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=cfg.llm_timeout_seconds)
    last_error = "The speech-to-text provider returned an error"
    try:
        for model in models:
            response = await http.post(
                f"{cfg.llm_base_url.rstrip('/')}/audio/transcriptions",
                json={**payload, "model": model},
                headers=_headers(cfg),
            )
            if response.status_code == 401:
                raise AppError(401, "unauthorized", "The speech-to-text provider rejected the API key")
            if response.status_code == 402:
                raise AppError(
                    402,
                    "stt_payment_required",
                    "OpenRouter needs credits for audio transcription. InterviewOS will transcribe on this device instead.",
                )
            if response.status_code in {404, 400} and model != _models(cfg)[-1]:
                logger.warning("STT model %s failed %s", model, response.status_code)
                continue
            if response.status_code >= 400:
                logger.warning("STT error %s %s", response.status_code, redact(response.text[:400]))
                last_error = "The speech-to-text provider returned an error"
                continue
            text = str((response.json() or {}).get("text") or "").strip()
            return text
    finally:
        if owns_client:
            await http.aclose()
    raise AppError(502, "stt_failed", last_error)
