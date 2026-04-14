"""Embedding service facade with pluggable providers."""

from __future__ import annotations

from pathlib import Path

from src.domain.models.document import Chunk
from src.domain.protocols.embedding import EmbeddingProvider
from src.indexing.providers.sentence_transformer import SentenceTransformerEmbeddingProvider
from src.indexing.providers.tfidf import TfidfEmbeddingProvider


class EmbeddingService:
    def __init__(
        self,
        dimensions: int = 2048,
        model_name_or_path: str | None = None,
        provider: EmbeddingProvider | None = None,
    ) -> None:
        self.dimensions = dimensions
        self.model_name_or_path = model_name_or_path
        self._provider = provider or self._build_provider(dimensions, model_name_or_path)

    @property
    def backend(self) -> str:
        return self._provider.backend

    def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        return self._provider.embed_texts([chunk.text for chunk in chunks])

    def embed_query(self, query: str) -> list[float]:
        return self._provider.embed_query(query)

    def save_state(self, output_dir: Path) -> None:
        self._provider.save_state(output_dir)

    def load_state(self, input_dir: Path) -> None:
        self._provider.load_state(input_dir)

    @staticmethod
    def _build_provider(
        dimensions: int,
        model_name_or_path: str | None,
    ) -> EmbeddingProvider:
        if model_name_or_path and Path(model_name_or_path).exists():
            try:
                return SentenceTransformerEmbeddingProvider(model_name_or_path)
            except Exception:
                pass
        return TfidfEmbeddingProvider(dimensions=dimensions)
