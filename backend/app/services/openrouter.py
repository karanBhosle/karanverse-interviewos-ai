"""Compatibility shim. Prefer app.services.llm."""

from app.services.llm import CompatibleLLMProvider as OpenRouterProvider
from app.services.llm import LLMError as OpenRouterError
from app.services.llm import LLMProvider, LLMResult, MockLLMProvider, parse_json_object

__all__ = [
    "OpenRouterError",
    "OpenRouterProvider",
    "LLMProvider",
    "LLMResult",
    "MockLLMProvider",
    "parse_json_object",
]
