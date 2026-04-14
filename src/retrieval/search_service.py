"""Search orchestration service."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from collections import defaultdict

import numpy as np

from src.indexing.bm25_index import Bm25Index
from src.indexing.embeddings import EmbeddingService
from src.indexing.index_builder import IndexBuilder
from src.indexing.vector_index import VectorIndex
from src.retrieval.hybrid_fusion import HybridFusion
from src.retrieval.rerank import NoOpReranker


class SearchService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_index: VectorIndex,
        bm25_index: Bm25Index,
        fusion: HybridFusion,
        reranker: NoOpReranker,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_index = vector_index
        self.bm25_index = bm25_index
        self.fusion = fusion
        self.reranker = reranker

    @property
    def embedding_backend(self) -> str:
        return getattr(self.embedding_service, "backend", "unknown")

    def search_chunks(
        self,
        query: str,
        top_k: int = 10,
        chunk_types: set[str] | None = None,
    ) -> list[dict]:
        query_vector = self.embedding_service.embed_query(query)
        bm25_results = self.bm25_index.search(query, top_k=max(top_k * 2, top_k))
        vector_results = self.vector_index.search(query_vector, top_k=max(top_k * 2, top_k))
        fused = self.fusion.fuse(bm25_results, vector_results, top_k=max(top_k * 3, top_k))
        filtered = self._filter_results(fused, chunk_types=chunk_types)
        reranked = self.reranker.rerank(query, filtered)
        deduplicated = self._deduplicate_results(reranked, chunk_types=chunk_types)
        collapsed = self._collapse_results(deduplicated, chunk_types=chunk_types)
        return collapsed[:top_k]

    def search_tables(self, query: str, top_k: int = 10) -> list[dict]:
        return self.search_chunks(query, top_k=top_k, chunk_types={"table"})

    @staticmethod
    def from_chunk_artifacts(
        chunks_dir: Path,
        embedding_model_path: str | None = None,
    ) -> "SearchService":
        embedding_service = EmbeddingService(model_name_or_path=embedding_model_path)
        vector_index = VectorIndex()
        bm25_index = Bm25Index()
        builder = IndexBuilder(
            embedding_service=embedding_service,
            vector_index=vector_index,
            bm25_index=bm25_index,
        )
        builder.build_from_chunk_files(chunks_dir)
        return SearchService(
            embedding_service=embedding_service,
            vector_index=vector_index,
            bm25_index=bm25_index,
            fusion=HybridFusion(),
            reranker=NoOpReranker(),
        )

    @staticmethod
    def from_persisted_index(
        index_dir: Path,
        embedding_model_path: str | None = None,
    ) -> "SearchService":
        manifest_path = index_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing manifest: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        resolved_model_path = embedding_model_path or manifest.get("embedding_model_path")
        embedding_service = EmbeddingService(model_name_or_path=resolved_model_path)
        embedding_service.load_state(index_dir)
        vector_index = VectorIndex()
        bm25_index = Bm25Index()

        chunks = IndexBuilder.load_chunks_metadata(index_dir / "chunks.json")
        vectors = np.load(index_dir / "vectors.npy").astype("float32").tolist()
        vector_index.add(chunks, vectors)
        bm25_index.add(chunks)

        return SearchService(
            embedding_service=embedding_service,
            vector_index=vector_index,
            bm25_index=bm25_index,
            fusion=HybridFusion(),
            reranker=NoOpReranker(),
        )

    @staticmethod
    def _filter_results(results: list[dict], chunk_types: set[str] | None) -> list[dict]:
        if not chunk_types:
            return results
        return [item for item in results if item["chunk"].chunk_type in chunk_types]

    @classmethod
    def _deduplicate_results(
        cls,
        results: list[dict],
        chunk_types: set[str] | None = None,
    ) -> list[dict]:
        deduplicated: list[dict] = []
        seen_text_signatures: set[str] = set()

        for item in results:
            chunk = item["chunk"]
            text_signature = cls._text_signature(chunk.text)
            if text_signature in seen_text_signatures:
                continue
            if cls._is_redundant_heading(item, deduplicated, chunk_types=chunk_types):
                continue
            seen_text_signatures.add(text_signature)
            deduplicated.append(item)
        return deduplicated

    @classmethod
    def _collapse_results(
        cls,
        results: list[dict],
        chunk_types: set[str] | None = None,
    ) -> list[dict]:
        grouped: dict[tuple[str, int, tuple[str, ...]], list[dict]] = defaultdict(list)
        for item in results:
            chunk = item["chunk"]
            key = (chunk.doc_id, chunk.page_no, tuple(chunk.section_path))
            grouped[key].append(item)

        collapsed: list[dict] = []
        for items in grouped.values():
            representative = max(items, key=cls._group_sort_key)
            collapsed.append(representative)

        collapsed.sort(key=cls._group_sort_key, reverse=True)
        return collapsed

    @classmethod
    def _is_redundant_heading(
        cls,
        candidate: dict,
        accepted: list[dict],
        chunk_types: set[str] | None = None,
    ) -> bool:
        chunk = candidate["chunk"]
        if chunk.chunk_type != "heading":
            return False
        if chunk_types == {"table"}:
            return False

        candidate_text = cls._normalize_text(chunk.text)
        if len(candidate_text) > 64:
            return False

        candidate_scope = (chunk.doc_id, chunk.page_no, tuple(chunk.section_path))
        for existing in accepted:
            existing_chunk = existing["chunk"]
            existing_scope = (
                existing_chunk.doc_id,
                existing_chunk.page_no,
                tuple(existing_chunk.section_path),
            )
            if existing_scope != candidate_scope:
                continue
            if existing_chunk.chunk_type == "heading":
                continue
            existing_text = cls._normalize_text(existing_chunk.text)
            if candidate_text and candidate_text in existing_text:
                return True
        return False

    @staticmethod
    def _text_signature(text: str) -> str:
        normalized = SearchService._normalize_text(text)
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.lower().split())

    @staticmethod
    def _group_sort_key(item: dict) -> tuple[int, float, int]:
        chunk = item["chunk"]
        type_priority = {
            "paragraph": 3,
            "mixed": 3,
            "table": 2,
            "figure_caption": 2,
            "heading": 1,
        }.get(chunk.chunk_type, 0)
        text_length = len(chunk.text.strip())
        score = float(item.get("score", 0.0)) - SearchService._toc_penalty(chunk)
        return (type_priority, score, text_length)

    @staticmethod
    def _toc_penalty(chunk) -> float:
        title = SearchService._normalize_text(" ".join(chunk.section_path))
        text = SearchService._normalize_text(chunk.text[:120])
        haystack = f"{title} {text}"
        toc_markers = (
            "目录",
            "图表目录",
            "contents",
            "table of contents",
            "figure index",
            "chart index",
        )
        if any(marker in haystack for marker in toc_markers):
            return 0.02
        return 0.0
