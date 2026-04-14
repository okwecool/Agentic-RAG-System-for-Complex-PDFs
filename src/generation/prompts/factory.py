"""Prompt template factory."""

from __future__ import annotations

from src.config.settings import Settings
from src.generation.prompts.base import BasePromptTemplate
from src.generation.prompts.chinese_generic import ChineseGenericPromptTemplate
from src.generation.prompts.qwen import QwenPromptTemplate


def create_prompt_template(settings: Settings) -> BasePromptTemplate:
    family = settings.llm_prompt_family.lower().strip()
    model_name = settings.llm_model_name.lower().strip()

    if family == "auto":
        if "qwen" in model_name:
            return QwenPromptTemplate()
        return ChineseGenericPromptTemplate()
    if family == "qwen":
        return QwenPromptTemplate()
    if family in {"zh", "zh_generic", "generic"}:
        return ChineseGenericPromptTemplate()
    raise ValueError(f"Unsupported prompt family: {settings.llm_prompt_family}")
