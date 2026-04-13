"""Reranker placeholder."""


class NoOpReranker:
    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        del query
        return candidates

