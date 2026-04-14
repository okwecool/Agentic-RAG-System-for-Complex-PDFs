"""TF-IDF embedding provider."""

from __future__ import annotations

from pathlib import Path
import pickle

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.indexing.providers.base import BaseEmbeddingProvider


class TfidfEmbeddingProvider(BaseEmbeddingProvider):
    backend = "tfidf"

    def __init__(self, dimensions: int = 2048) -> None:
        self.dimensions = dimensions
        self._vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            max_features=dimensions,
            lowercase=True,
        )
        self._fitted = False

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        matrix = self._vectorizer.fit_transform(texts)
        self._fitted = True
        return self._normalize_dense(matrix.toarray()).tolist()

    def embed_query(self, query: str) -> list[float]:
        if not self._fitted:
            raise RuntimeError("Embedding provider must fit chunk vectors before query embedding.")
        matrix = self._vectorizer.transform([query])
        return self._normalize_dense(matrix.toarray())[0].tolist()

    def save_state(self, output_dir: Path) -> None:
        with (output_dir / "vectorizer.pkl").open("wb") as handle:
            pickle.dump(self._vectorizer, handle)

    def load_state(self, input_dir: Path) -> None:
        vectorizer_path = input_dir / "vectorizer.pkl"
        if not vectorizer_path.exists():
            return
        with vectorizer_path.open("rb") as handle:
            self._vectorizer = pickle.load(handle)
        self._fitted = True

    @staticmethod
    def _normalize_dense(matrix: np.ndarray) -> np.ndarray:
        dense = np.asarray(matrix, dtype="float32")
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return dense / norms
