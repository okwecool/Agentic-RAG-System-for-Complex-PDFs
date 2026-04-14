"""Hybrid fusion helpers."""

from __future__ import annotations


class HybridFusion:
    def __init__(
        self,
        mode: str = "rrf",
        rrf_k: int = 60,
        bm25_weight: float = 1.0,
        vector_weight: float = 1.0,
    ) -> None:
        self.mode = mode
        self.rrf_k = rrf_k
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight

    def describe(self) -> dict[str, float | int | str]:
        return {
            "mode": self.mode,
            "rrf_k": self.rrf_k,
            "bm25_weight": self.bm25_weight,
            "vector_weight": self.vector_weight,
        }

    def fuse(self, bm25_results: list[dict], vector_results: list[dict], top_k: int) -> list[dict]:
        aggregated: dict[str, dict] = {}
        self._accumulate(aggregated, bm25_results, source_weight=self.bm25_weight)
        self._accumulate(aggregated, vector_results, source_weight=self.vector_weight)

        fused = sorted(
            aggregated.values(),
            key=lambda item: item["score"],
            reverse=True,
        )
        return fused[:top_k]

    def _accumulate(
        self,
        aggregated: dict[str, dict],
        results: list[dict],
        source_weight: float,
    ) -> None:
        total = max(len(results), 1)
        for rank, item in enumerate(results, start=1):
            chunk = item["chunk"]
            chunk_id = chunk.chunk_id
            fusion_score = self._fusion_score(
                rank=rank,
                total=total,
                raw_score=float(item["score"]),
                source_weight=source_weight,
            )
            if chunk_id not in aggregated:
                aggregated[chunk_id] = {
                    "chunk": chunk,
                    "score": 0.0,
                    "sources": [],
                    "component_scores": {},
                }
            aggregated_item = aggregated[chunk_id]
            aggregated_item["score"] += fusion_score
            aggregated_item["sources"].append(item["source"])
            aggregated_item["component_scores"][item["source"]] = item["score"]

    def _fusion_score(
        self,
        rank: int,
        total: int,
        raw_score: float,
        source_weight: float,
    ) -> float:
        del raw_score
        if self.mode == "rrf":
            return source_weight * (1.0 / (self.rrf_k + rank))
        if self.mode == "weighted_rank":
            return source_weight * ((total - rank + 1) / total)
        raise ValueError(f"Unsupported fusion mode: {self.mode}")
