"""Hybrid fusion helpers."""

from __future__ import annotations


class HybridFusion:
    def __init__(self, rrf_k: int = 60) -> None:
        self.rrf_k = rrf_k

    def fuse(self, bm25_results: list[dict], vector_results: list[dict], top_k: int) -> list[dict]:
        aggregated: dict[str, dict] = {}
        self._accumulate(aggregated, bm25_results)
        self._accumulate(aggregated, vector_results)

        fused = sorted(
            aggregated.values(),
            key=lambda item: item["score"],
            reverse=True,
        )
        return fused[:top_k]

    def _accumulate(self, aggregated: dict[str, dict], results: list[dict]) -> None:
        for rank, item in enumerate(results, start=1):
            chunk = item["chunk"]
            chunk_id = chunk.chunk_id
            rrf_score = 1.0 / (self.rrf_k + rank)
            if chunk_id not in aggregated:
                aggregated[chunk_id] = {
                    "chunk": chunk,
                    "score": 0.0,
                    "sources": [],
                    "component_scores": {},
                }
            aggregated_item = aggregated[chunk_id]
            aggregated_item["score"] += rrf_score
            aggregated_item["sources"].append(item["source"])
            aggregated_item["component_scores"][item["source"]] = item["score"]
