"""Hybrid fusion helpers."""


class HybridFusion:
    def fuse(self, bm25_results: list[dict], vector_results: list[dict], top_k: int) -> list[dict]:
        seen: set[str] = set()
        fused: list[dict] = []
        for item in bm25_results + vector_results:
            chunk = item["chunk"]
            chunk_id = getattr(chunk, "chunk_id", None)
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            fused.append(item)
            if len(fused) >= top_k:
                break
        return fused

