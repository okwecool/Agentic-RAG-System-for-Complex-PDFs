"""In-memory vector index with cosine similarity search."""

from __future__ import annotations

from src.domain.models.document import Chunk


class VectorIndex:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Chunk and vector counts must match.")
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)

    def search(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        scored: list[dict] = []
        for chunk, vector in zip(self._chunks, self._vectors):
            score = self._cosine_similarity(query_vector, vector)
            if score <= 0.0:
                continue
            scored.append({"chunk": chunk, "score": score, "source": "vector"})

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if len(left) != len(right):
            raise ValueError("Vector dimensions must match.")
        return sum(left_value * right_value for left_value, right_value in zip(left, right))
