"""Embedding provider protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class EmbeddingProvider(Protocol):
    backend: str
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Encode document texts."""

    def embed_query(self, query: str) -> list[float]:
        """Encode a single query."""

    def save_state(self, output_dir: Path) -> None:
        """Persist provider-specific state when needed."""

    def load_state(self, input_dir: Path) -> None:
        """Restore provider-specific state when needed."""
