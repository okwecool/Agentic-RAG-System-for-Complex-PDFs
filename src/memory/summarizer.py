"""Conversation summarization helpers."""

from __future__ import annotations


class ConversationSummarizer:
    def summarize(self, messages: list[dict]) -> str:
        snippets: list[str] = []
        for item in messages[-6:]:
            role = item.get("role", "unknown")
            content = " ".join(str(item.get("content", "")).split())
            if not content:
                continue
            snippets.append(f"{role}: {content[:120]}")
        return "\n".join(snippets)

