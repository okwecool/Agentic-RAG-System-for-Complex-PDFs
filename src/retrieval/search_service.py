"""Search orchestration service."""

from __future__ import annotations

from collections import defaultdict
import json
import logging
from pathlib import Path

import numpy as np

from src.indexing.bm25_index import Bm25Index
from src.indexing.embeddings import EmbeddingService
from src.indexing.index_builder import IndexBuilder
from src.indexing.vector_index import VectorIndex
from src.domain.protocols.reranker import RerankerProvider
from src.retrieval.factory import create_hybrid_fusion, create_reranker
from src.retrieval.hybrid_fusion import HybridFusion
from src.retrieval.rerank import NoOpReranker
from src.retrieval.signals import QuerySignature, SearchSignals

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_index: VectorIndex,
        bm25_index: Bm25Index,
        fusion: HybridFusion,
        reranker: RerankerProvider,
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
        logger.info(
            "search.start query=%r top_k=%s chunk_types=%s embedding=%s fusion=%s reranker=%s",
            query,
            top_k,
            sorted(chunk_types) if chunk_types else "all",
            self.embedding_backend,
            self.fusion.describe(),
            self.describe_reranker(),
        )
        query_vector = self.embedding_service.embed_query(query)
        bm25_results = self.bm25_index.search(query, top_k=max(top_k * 2, top_k))
        vector_results = self.vector_index.search(query_vector, top_k=max(top_k * 2, top_k))
        logger.info(
            "search.stage_recall bm25_hits=%s vector_hits=%s",
            len(bm25_results),
            len(vector_results),
        )
        fused = self.fusion.fuse(bm25_results, vector_results, top_k=max(top_k * 3, top_k))
        filtered = self._filter_results(fused, chunk_types=chunk_types)
        reranked = self.reranker.rerank(query, filtered)
        deduplicated = self._deduplicate_results(reranked, chunk_types=chunk_types)
        query_signature = SearchSignals.build_query_signature(query)
        collapsed = self._collapse_results(
            deduplicated,
            query_signature=query_signature,
            chunk_types=chunk_types,
        )
        logger.info(
            "search.stage_rank fused=%s filtered=%s reranked=%s deduplicated=%s collapsed=%s",
            len(fused),
            len(filtered),
            len(reranked),
            len(deduplicated),
            len(collapsed),
        )
        return collapsed[:top_k]

    def search_tables(self, query: str, top_k: int = 10) -> list[dict]:
        return self.search_chunks(query, top_k=top_k, chunk_types={"table"})

    @staticmethod
    def from_chunk_artifacts(
        chunks_dir: Path,
        embedding_model_path: str | None = None,
        fusion: HybridFusion | None = None,
        reranker: RerankerProvider | None = None,
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
            fusion=fusion or HybridFusion(),
            reranker=reranker or NoOpReranker(),
        )

    @staticmethod
    def from_persisted_index(
        index_dir: Path,
        embedding_model_path: str | None = None,
        fusion: HybridFusion | None = None,
        reranker: RerankerProvider | None = None,
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
            fusion=fusion or HybridFusion(),
            reranker=reranker or NoOpReranker(),
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
        query_signature: QuerySignature | None = None,
        chunk_types: set[str] | None = None,
    ) -> list[dict]:
        grouped: dict[tuple[str, int, tuple[str, ...]], list[dict]] = defaultdict(list)
        for item in results:
            chunk = item["chunk"]
            key = (chunk.doc_id, chunk.page_no, tuple(chunk.section_path))
            grouped[key].append(item)

        collapsed: list[dict] = []
        for items in grouped.values():
            representative = max(
                items,
                key=lambda current: cls._group_sort_key(
                    current,
                    query_signature=query_signature,
                ),
            )
            collapsed.append(representative)

        collapsed.sort(
            key=lambda current: cls._group_sort_key(
                current,
                query_signature=query_signature,
            ),
            reverse=True,
        )
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
        return SearchSignals.text_signature(text)

    @staticmethod
    def _normalize_text(text: str) -> str:
        return SearchSignals.normalize_text(text)

    @staticmethod
    def _group_sort_key(
        item: dict,
        query_signature: QuerySignature | None = None,
    ) -> tuple[int, float, int]:
        return SearchSignals.representative_rank_key(
            item,
            query_signature=query_signature,
        )

    def describe_reranker(self) -> dict[str, str | int]:
        describe = getattr(self.reranker, "describe", None)
        if callable(describe):
            return describe()
        return {
            "backend": getattr(self.reranker, "backend", "unknown"),
            "model_name": getattr(self.reranker, "model_name", "unknown"),
        }
