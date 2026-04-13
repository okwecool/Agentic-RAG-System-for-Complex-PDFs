"""Vector index with FAISS-backed search and in-memory fallback."""

from __future__ import annotations

import numpy as np

from src.domain.models.document import Chunk


class VectorIndex:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []
        self._faiss = self._load_faiss()
        self._index = None
        self._dimension: int | None = None

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Chunk and vector counts must match.")
        if not vectors:
            return

        matrix = np.asarray(vectors, dtype="float32")
        if matrix.ndim != 2:
            raise ValueError("Vectors must be a 2D matrix.")

        self._chunks.extend(chunks)
        self._vectors.extend(matrix.tolist())

        if self._faiss is None:
            return

        if self._index is None:
            self._dimension = int(matrix.shape[1])
            self._index = self._faiss.IndexFlatIP(self._dimension)

        self._index.add(matrix)

    def search(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        if not self._chunks:
            return []
        if self._faiss is not None and self._index is not None:
            return self._search_faiss(query_vector, top_k)
        return self._search_in_memory(query_vector, top_k)

    def _search_faiss(self, query_vector: list[float], top_k: int) -> list[dict]:
        query = np.asarray([query_vector], dtype="float32")
        scores, indices = self._index.search(query, min(top_k, len(self._chunks)))
        results: list[dict] = []
        for score, index in zip(scores[0], indices[0]):
            if index < 0 or score <= 0.0:
                continue
            results.append(
                {
                    "chunk": self._chunks[int(index)],
                    "score": float(score),
                    "source": "vector",
                }
            )
        return results

    def _search_in_memory(self, query_vector: list[float], top_k: int) -> list[dict]:
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

    @staticmethod
    def _load_faiss():
        try:
            import faiss
        except ModuleNotFoundError:
            return None
        return faiss
