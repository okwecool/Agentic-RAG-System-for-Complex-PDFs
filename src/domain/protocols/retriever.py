"""Retriever protocol."""

from typing import Any, Protocol


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Return retrieval candidates."""

