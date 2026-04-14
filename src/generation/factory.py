"""LLM provider factory helpers."""

from __future__ import annotations

from src.config.settings import Settings
from src.domain.protocols.llm import LlmProvider
from src.generation.providers.local_stub import LocalStubLlmProvider
from src.generation.providers.openai_compatible import OpenAiCompatibleLlmProvider


def create_llm_provider(settings: Settings) -> LlmProvider:
    provider_name = settings.llm_provider.lower().strip()
    if provider_name == "openai_compatible":
        if not settings.dashscope_api_key:
            raise ValueError("Missing DASHSCOPE_API_KEY for OpenAI-compatible LLM provider.")
        if not settings.dashscope_base_url:
            raise ValueError("Missing DASHSCOPE_BASE_URL for OpenAI-compatible LLM provider.")
        return OpenAiCompatibleLlmProvider(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            model_name=settings.llm_model_name,
        )
    if provider_name == "local":
        return LocalStubLlmProvider(model_name=settings.llm_model_name)
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
