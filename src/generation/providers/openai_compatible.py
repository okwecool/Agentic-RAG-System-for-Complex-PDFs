"""OpenAI-compatible LLM provider."""

from __future__ import annotations

from openai import OpenAI

from src.generation.providers.base import BaseLlmProvider


class OpenAiCompatibleLlmProvider(BaseLlmProvider):
    backend = "openai_compatible"

    def __init__(self, api_key: str, base_url: str, model_name: str) -> None:
        super().__init__(model_name=model_name)
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        message = response.choices[0].message.content or ""
        return message.strip()
