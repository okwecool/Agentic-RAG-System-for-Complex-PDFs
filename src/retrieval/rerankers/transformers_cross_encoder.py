"""Transformers-based local cross-encoder reranker."""

from __future__ import annotations

from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.retrieval.rerankers.base import BaseRerankerProvider


class TransformersCrossEncoderReranker(BaseRerankerProvider):
    backend = "transformers_cross_encoder"

    def __init__(
        self,
        model_name_or_path: str,
        top_n: int = 20,
        batch_size: int = 8,
        device: str | None = None,
    ) -> None:
        super().__init__(model_name=str(model_name_or_path))
        self.model_path = str(model_name_or_path)
        self.top_n = top_n
        self.batch_size = batch_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = None
        self._model = None

    def describe(self) -> dict[str, str | int]:
        return {
            "backend": self.backend,
            "model_name": self.model_name,
            "top_n": self.top_n,
            "batch_size": self.batch_size,
            "device": self.device,
        }

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        if len(candidates) <= 1:
            return candidates

        rerank_scope = candidates[: self.top_n]
        remainder = candidates[self.top_n :]
        scores = self._score_pairs(query, rerank_scope)

        reranked_scope: list[dict] = []
        for item, score in zip(rerank_scope, scores):
            updated = dict(item)
            updated["rerank_score"] = float(score)
            updated["score"] = float(score)
            reranked_scope.append(updated)

        reranked_scope.sort(key=lambda item: item["score"], reverse=True)
        return reranked_scope + remainder

    def _load(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return
        model_path = Path(self.model_path)
        self._tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            local_files_only=True,
        )
        self._model.to(self.device)
        self._model.eval()

    def _score_pairs(self, query: str, candidates: list[dict]) -> list[float]:
        self._load()
        assert self._tokenizer is not None
        assert self._model is not None

        all_scores: list[float] = []
        texts = [item["chunk"].text for item in candidates]

        for start in range(0, len(texts), self.batch_size):
            batch_texts = texts[start : start + self.batch_size]
            encoded = self._tokenizer(
                [query] * len(batch_texts),
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with torch.no_grad():
                logits = self._model(**encoded).logits
                batch_scores = logits.view(-1).detach().cpu().tolist()
            all_scores.extend(float(score) for score in batch_scores)
        return all_scores
