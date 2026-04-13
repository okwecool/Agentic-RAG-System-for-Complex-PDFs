"""Local embedding service used for baseline retrieval."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.domain.models.document import Chunk


class EmbeddingService:
    def __init__(
        self,
        dimensions: int = 2048,
        model_name_or_path: str | None = None,
    ) -> None:
        self.dimensions = dimensions
        self.model_name_or_path = model_name_or_path
        self.backend = "tfidf"
        self._vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            max_features=dimensions,
            lowercase=True,
        )
        self._model = None
        self._fitted = False

        if model_name_or_path and Path(model_name_or_path).exists():
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(model_name_or_path, device="cpu")
                self.backend = "sentence_transformer"
            except Exception:
                self._model = None
                self.backend = "tfidf"

    def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        texts = [chunk.text for chunk in chunks]
        if self._model is not None:
            matrix = self._model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=16,
                show_progress_bar=True,
            )
            return np.asarray(matrix, dtype="float32").tolist()

        if not texts:
            return []
        matrix = self._vectorizer.fit_transform(texts)
        self._fitted = True
        return self._normalize_dense(matrix.toarray()).tolist()

    def embed_query(self, query: str) -> list[float]:
        if self._model is not None:
            vector = self._model.encode(
                [query],
                normalize_embeddings=True,
                batch_size=1,
                show_progress_bar=False,
            )[0]
            return np.asarray(vector, dtype="float32").tolist()

        if not self._fitted:
            raise RuntimeError("EmbeddingService must fit chunk vectors before query embedding.")
        matrix = self._vectorizer.transform([query])
        return self._normalize_dense(matrix.toarray())[0].tolist()

    @staticmethod
    def _normalize_dense(matrix: np.ndarray) -> np.ndarray:
        dense = np.asarray(matrix, dtype="float32")
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return dense / norms
