from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import redact

logger = logging.getLogger(__name__)


class LLMError(Exception):
    def __init__(self, code: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass
class LLMResult:
    content: str
    model: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict[str, Any] | None = None


class LLMProvider:
    async def complete_json(self, *, system: str, user: str, schema_name: str) -> LLMResult:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    def __init__(self, payload: dict[str, Any] | None = None):
        self.payload = payload or {}
        self.calls: list[dict[str, str]] = []

    async def complete_json(self, *, system: str, user: str, schema_name: str) -> LLMResult:
        self.calls.append({"system": system, "user": user, "schema_name": schema_name})
        return LLMResult(
            content=json.dumps(self.payload),
            model="mock",
            latency_ms=1.0,
            prompt_tokens=10,
            completion_tokens=10,
        )


class CompatibleLLMProvider(LLMProvider):
    """Any OpenAI-compatible Chat Completions API (OpenAI, Azure, Groq, OpenRouter, local servers)."""

    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self._client = client

    @property
    def available(self) -> bool:
        return self.settings.llm_configured

    def pick_model(self) -> str:
        pool = self.settings.llm_model_pool
        if not pool:
            return self.settings.llm_model
        if self.settings.llm_model.strip().lower() in {"random", "auto", "openrouter/free"} or len(pool) > 1:
            return random.choice(pool)
        return pool[0]

    async def complete_json(self, *, system: str, user: str, schema_name: str) -> LLMResult:
        if not self.available:
            raise LLMError("provider_unavailable", "LLM_API_KEY and LLM_BASE_URL are not configured")
        body = {
            "model": self.pick_model(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self.settings.llm_max_output_tokens,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        if self.settings.llm_http_referer:
            headers["HTTP-Referer"] = self.settings.llm_http_referer
        if self.settings.llm_app_name:
            headers["X-Title"] = self.settings.llm_app_name
        delay = 0.6
        last_error: Exception | None = None
        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                return await self._post(body, headers)
            except LLMError as exc:
                last_error = exc
                if exc.status_code in {401}:
                    raise
                if exc.status_code not in {429, 500, 502, 503, 504} and exc.code != "empty_response":
                    raise
                if attempt >= self.settings.llm_max_retries:
                    raise
                await asyncio.sleep(delay)
                delay *= 2
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt >= self.settings.llm_max_retries:
                    raise LLMError("timeout", "LLM request timed out") from exc
                await asyncio.sleep(delay)
                delay *= 2
        raise LLMError("provider_error", str(last_error) if last_error else "unknown")

    async def _post(self, body: dict[str, Any], headers: dict[str, str]) -> LLMResult:
        started = asyncio.get_event_loop().time()
        client = self._client or httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds)
        owns_client = self._client is None
        try:
            response = await client.post(
                f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                json=body,
                headers=headers,
            )
        finally:
            if owns_client:
                await client.aclose()
        latency_ms = (asyncio.get_event_loop().time() - started) * 1000
        if response.status_code == 401:
            logger.warning("LLM authentication failed")
            raise LLMError("unauthorized", "The LLM provider rejected the API key", 401)
        if response.status_code == 429:
            raise LLMError("rate_limited", "The LLM provider rate limited the request", 429)
        if response.status_code >= 400:
            logger.warning("LLM error %s %s", response.status_code, redact(response.text[:400]))
            raise LLMError("provider_error", "The LLM provider returned an error", response.status_code)
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("empty_response", "The LLM provider returned no choices")
        content = (choices[0].get("message") or {}).get("content") or ""
        if not content.strip():
            raise LLMError("empty_response", "The LLM provider returned an empty message")
        usage = data.get("usage") or {}
        return LLMResult(
            content=content,
            model=data.get("model") or self.settings.llm_model,
            latency_ms=latency_ms,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            raw=data,
        )


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned)
