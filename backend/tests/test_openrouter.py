"""Legacy import path still resolves to the generic LLM client."""

from app.services.llm import CompatibleLLMProvider, LLMError
from app.services.openrouter import OpenRouterError, OpenRouterProvider


def test_legacy_names_are_aliases():
    assert OpenRouterProvider is CompatibleLLMProvider
    assert OpenRouterError is LLMError
