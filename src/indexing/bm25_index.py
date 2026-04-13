"""BM25 index placeholder."""

from src.domain.models.document import Chunk


class Bm25Index:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    def add(self, chunks: list[Chunk]) -> None:
        self._chunks.extend(chunks)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        del query
        return [
            {"chunk": chunk, "score": 0.0, "source": "bm25"}
            for chunk in self._chunks[:top_k]
        ]

