from __future__ import annotations

import hashlib
import io
from collections import OrderedDict

from app.core.config import get_settings
from app.core.errors import ValidationAppError

MAX_CHARS = 4_000
CACHE_SIZE = 32
DEFAULT_VOICE = "en-IN-NeerjaNeural"
DEFAULT_CONTENT_TYPE = "audio/mpeg"

_cache: OrderedDict[str, tuple[bytes, str, str]] = OrderedDict()


def _cache_key(text: str, voice: str, rate: str, pitch: str) -> str:
    raw = f"{voice}|{rate}|{pitch}|{text}".encode()
    return hashlib.sha256(raw).hexdigest()


def _remember(key: str, payload: tuple[bytes, str, str]) -> tuple[bytes, str, str]:
    _cache[key] = payload
    _cache.move_to_end(key)
    while len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return payload


async def synthesize(text: str, voice: str | None = None) -> tuple[bytes, str, str]:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        raise ValidationAppError("There is no question text to speak.")
    if len(cleaned) > MAX_CHARS:
        raise ValidationAppError("Question text is too long to speak in one turn.")
    settings = get_settings()
    chosen = (voice or settings.tts_voice or DEFAULT_VOICE).strip() or DEFAULT_VOICE
    key = _cache_key(cleaned, chosen, settings.tts_rate, settings.tts_pitch)
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    audio, content_type = await _neural_indian(cleaned, chosen, settings.tts_rate, settings.tts_pitch)
    return _remember(key, (audio, content_type, chosen))


async def _neural_indian(text: str, voice: str, rate: str, pitch: str) -> tuple[bytes, str]:
    try:
        import edge_tts
    except ImportError as exc:
        raise ValidationAppError("Neural TTS is not installed on the API.") from exc
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            buffer.write(chunk["data"])
    audio = buffer.getvalue()
    if not audio:
        raise ValidationAppError("The interviewer voice could not be generated.")
    return audio, DEFAULT_CONTENT_TYPE
