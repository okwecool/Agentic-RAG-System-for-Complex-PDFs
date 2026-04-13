"""Embedding model abstraction placeholder."""

from src.domain.models.document import Chunk


class EmbeddingService:
    def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        return [[0.0] * 8 for _ in chunks]

    def embed_query(self, query: str) -> list[float]:
        return [0.0] * 8

