import json

import httpx
import pytest

from app.core.config import Settings
from app.core.logging import redact
from app.services.llm import CompatibleLLMProvider, LLMError, parse_json_object


def test_redacts_secrets():
    text = redact("Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz Authorization=secret")
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in text
    assert "***REDACTED***" in text


@pytest.mark.asyncio
async def test_llm_401():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "nope"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = CompatibleLLMProvider(
        settings=Settings(llm_api_key="sk-test", llm_max_retries=0),
        client=client,
    )
    with pytest.raises(LLMError) as exc:
        await provider.complete_json(system="s", user="u", schema_name="x")
    assert exc.value.code == "unauthorized"


@pytest.mark.asyncio
async def test_empty_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = CompatibleLLMProvider(
        settings=Settings(llm_api_key="sk-test", llm_max_retries=0),
        client=client,
    )
    with pytest.raises(LLMError) as exc:
        await provider.complete_json(system="s", user="u", schema_name="x")
    assert exc.value.code == "empty_response"


def test_parse_json_object():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert json.dumps(parse_json_object('{"ok": true}'))


def test_legacy_openrouter_env_alias(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-legacy")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    settings = Settings(_env_file=None)
    assert settings.llm_api_key == "sk-legacy"
    assert settings.llm_configured
