"""Qwen-oriented Chinese QA prompt template."""

from __future__ import annotations

from src.generation.prompts.base import BasePromptTemplate, PromptBundle
from src.generation.prompts.chinese_generic import _format_conversation_context, _format_evidence


class QwenPromptTemplate(BasePromptTemplate):
    family = "qwen"

    def build(
        self,
        query: str,
        evidence: list[dict],
        conversation_context: dict | None = None,
    ) -> PromptBundle:
        context = _format_evidence(evidence)
        conversation_block = _format_conversation_context(conversation_context)
        return PromptBundle(
            system_prompt=(
                "你是一个严谨的 PDF 问答助手。"
                "你必须严格依据提供的证据回答，不得补充证据中没有的信息。"
                "如果证据不足或证据之间无法支持明确结论，请直接说明无法确定。"
                "回答使用中文，优先给出结论，再给出必要说明。"
            ),
            user_prompt=(
                "请阅读下面的问题和证据后作答。\n\n"
                f"问题：\n{query}\n\n"
                f"{conversation_block}"
                f"证据：\n{context}\n\n"
                "输出要求：\n"
                "1. 只根据证据回答。\n"
                "2. 不要编造数值、时间或结论。\n"
                "3. 若证据不足，请明确写出“根据当前证据无法确定”。\n"
                "4. 回答保持简洁、清晰。"
            ),
        )
