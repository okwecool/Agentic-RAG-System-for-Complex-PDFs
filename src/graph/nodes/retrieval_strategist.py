"""Retrieval strategist node with optional SearchService integration."""

from __future__ import annotations

import logging

from src.config.settings import Settings
from src.domain.models.state import ResearchState
from src.retrieval.factory import create_hybrid_fusion, create_reranker
from src.retrieval.search_service import SearchService

logger = logging.getLogger(__name__)


class RetrievalStrategistNode:
    def __init__(
        self,
        search_service: SearchService | None = None,
        default_top_k: int = 6,
        strict: bool = False,
    ) -> None:
        self.search_service = search_service
        self.default_top_k = default_top_k
        self.strict = strict

    @classmethod
    def from_settings(cls, settings: Settings) -> "RetrievalStrategistNode":
        fusion = create_hybrid_fusion(settings)
        reranker = create_reranker(settings)
        if settings.retrieval_index_dir and settings.retrieval_index_dir.exists():
            search_service = SearchService.from_persisted_index(
                index_dir=settings.retrieval_index_dir,
                embedding_model_path=str(settings.local_embedding_model_dir)
                if settings.local_embedding_model_dir
                else None,
                fusion=fusion,
                reranker=reranker,
            )
        else:
            search_service = SearchService.from_chunk_artifacts(
                chunks_dir=settings.chunks_dir,
                embedding_model_path=str(settings.local_embedding_model_dir)
                if settings.local_embedding_model_dir
                else None,
                fusion=fusion,
                reranker=reranker,
            )
        return cls(search_service=search_service, default_top_k=settings.qa_top_k, strict=True)

    def run(self, state: ResearchState) -> ResearchState:
        if self.search_service is not None:
            plan = state.get("retrieval_plan", {})
            query = self._build_search_query(
                state.get("normalized_query") or state.get("user_query") or "",
                plan,
            )
            top_k = int(plan.get("top_k", self.default_top_k))
            tables_only = bool(plan.get("tables_only", False))
            state["retrieval_query"] = query
            logger.info(
                "retrieval.plan query=%r top_k=%s tables_only=%s intent=%s prefers_structured=%s entity_scope=%s time_terms=%s",
                query,
                top_k,
                tables_only,
                plan.get("intent"),
                plan.get("prefers_structured_blocks"),
                plan.get("entity_scope", []),
                plan.get("time_terms", []),
            )
            if query:
                results = (
                    self.search_service.search_tables(query, top_k=top_k)
                    if tables_only
                    else self.search_service.search_chunks(query, top_k=top_k)
                )
                state["retrieved_candidates"] = results
                state["selected_evidence"] = results[:top_k]
                state["candidate_evidence_types"] = [
                    self._infer_evidence_type(candidate)
                    for candidate in state["retrieved_candidates"]
                ]
                state["selected_evidence_types"] = [
                    self._infer_evidence_type(evidence)
                    for evidence in state["selected_evidence"]
                ]
                state["document_source_types"] = [
                    self._infer_document_source_type(candidate)
                    for candidate in state["selected_evidence"]
                ]
                state["embedding_backend"] = getattr(
                    self.search_service,
                    "embedding_backend",
                    "unknown",
                )
                state["retry_count"] = int(state.get("retry_count", 0) or 0) + 1
                logger.info(
                    "retrieval.result retrieved=%s selected=%s candidate_types=%s selected_types=%s document_source_types=%s retry_count=%s embedding=%s",
                    len(state["retrieved_candidates"]),
                    len(state["selected_evidence"]),
                    state["candidate_evidence_types"],
                    state["selected_evidence_types"],
                    state["document_source_types"],
                    state["retry_count"],
                    state["embedding_backend"],
                )
                return state

        if self.strict:
            raise RuntimeError("RetrievalStrategistNode requires a SearchService in strict mode.")

        if not state.get("retrieved_candidates"):
            state["retrieved_candidates"] = [
                {
                    "chunk_id": "placeholder_chunk",
                    "doc_id": "placeholder_doc",
                    "page_no": 1,
                    "score": 0.0,
                    "evidence_type": "narrative_evidence",
                }
            ]
        if not state.get("selected_evidence"):
            state["selected_evidence"] = list(state["retrieved_candidates"])
        if not state.get("candidate_evidence_types"):
            state["candidate_evidence_types"] = [
                candidate.get("evidence_type", "narrative_evidence")
                for candidate in state["retrieved_candidates"]
            ]
        if not state.get("selected_evidence_types"):
            state["selected_evidence_types"] = [
                evidence.get("evidence_type", "narrative_evidence")
                for evidence in state["selected_evidence"]
            ]
        state.setdefault("document_source_types", ["unknown"])
        state.setdefault("embedding_backend", "unknown")
        state["retry_count"] = int(state.get("retry_count", 0) or 0) + 1
        logger.info(
            "retrieval.placeholder retrieved=%s selected=%s selected_types=%s retry_count=%s",
            len(state["retrieved_candidates"]),
            len(state["selected_evidence"]),
            state["selected_evidence_types"],
            state["retry_count"],
        )
        return state

    @staticmethod
    def _build_search_query(base_query: str, plan: dict) -> str:
        query = " ".join(str(base_query or "").strip().split())
        enrichment_terms: list[str] = []
        for term in plan.get("entity_scope", []) or []:
            normalized = str(term).strip()
            if normalized and normalized not in query and normalized not in enrichment_terms:
                enrichment_terms.append(normalized)
        topic_scope = plan.get("topic_scope", {}) or {}
        if isinstance(topic_scope, dict):
            for key in ("product", "topic"):
                normalized = str(topic_scope.get(key, "")).strip()
                if normalized and normalized not in query and normalized not in enrichment_terms:
                    enrichment_terms.append(normalized)
        for term in plan.get("time_terms", []) or []:
            normalized = str(term).strip()
            if normalized and normalized not in query and normalized not in enrichment_terms:
                enrichment_terms.append(normalized)

        if enrichment_terms:
            query = " ".join([query, *enrichment_terms]).strip()
        return query

    @staticmethod
    def _infer_evidence_type(item: dict) -> str:
        if "evidence_type" in item and item["evidence_type"]:
            return str(item["evidence_type"])

        chunk = item.get("chunk")
        if chunk is None:
            return "narrative_evidence"

        explicit = getattr(chunk, "evidence_type", None)
        if explicit:
            return str(explicit)

        metadata = getattr(chunk, "metadata", {}) or {}
        if metadata.get("evidence_type"):
            return str(metadata["evidence_type"])

        chunk_type = getattr(chunk, "chunk_type", "paragraph")
        if chunk_type == "table":
            return "table_evidence"
        if chunk_type == "heading":
            return "caption_evidence"
        if chunk_type in {"mixed", "figure_caption"}:
            return "chart_evidence"
        return "narrative_evidence"

    @staticmethod
    def _infer_document_source_type(item: dict) -> str:
        chunk = item.get("chunk")
        if chunk is None:
            return "unknown"
        metadata = getattr(chunk, "metadata", {}) or {}
        return str(
            metadata.get("document_source_type")
            or metadata.get("doc_type")
            or "unknown"
        )

