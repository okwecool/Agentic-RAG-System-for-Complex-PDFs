"""Vector index placeholder."""

from src.domain.models.document import Chunk


class VectorIndex:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)

    def search(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        del query_vector
        return [
            {"chunk": chunk, "score": 0.0, "source": "vector"}
            for chunk in self._chunks[:top_k]
        ]

