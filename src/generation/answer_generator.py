"""Answer generation built on top of pluggable LLM providers."""

from __future__ import annotations

from src.domain.protocols.llm import LlmProvider
from src.generation.prompts.base import BasePromptTemplate


class AnswerGenerator:
    def __init__(
        self,
        llm_provider: LlmProvider,
        prompt_template: BasePromptTemplate,
    ) -> None:
        self.llm_provider = llm_provider
        self.prompt_template = prompt_template

    def generate(
        self,
        query: str,
        evidence: list[dict],
        conversation_context: dict | None = None,
    ) -> dict:
        if not evidence:
            return {
                "answer": "根据当前检索到的 PDF 证据，暂时无法确定答案。",
                "claims": [],
                "confidence": "low",
                "model": self.llm_provider.model_name,
                "prompt_family": self.prompt_template.family,
            }

        prompt = self.prompt_template.build(
            query=query,
            evidence=evidence,
            conversation_context=conversation_context,
        )
        answer = self.llm_provider.generate(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
        )
        supporting_chunk_ids = [
            item["chunk"].chunk_id for item in evidence if "chunk" in item
        ]
        return {
            "answer": answer,
            "claims": [
                {
                    "claim": answer,
                    "supporting_chunk_ids": supporting_chunk_ids,
                }
            ],
            "confidence": "medium" if supporting_chunk_ids else "low",
            "model": self.llm_provider.model_name,
            "prompt_family": self.prompt_template.family,
        }
