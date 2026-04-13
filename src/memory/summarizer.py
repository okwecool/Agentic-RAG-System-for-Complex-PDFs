"""Conversation summarization placeholder."""


class ConversationSummarizer:
    def summarize(self, messages: list[str]) -> str:
        return "\n".join(messages[-5:])

