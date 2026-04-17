"""Agentic QA service built on top of QueryWorkflow."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass

from src.config.settings import Settings
from src.domain.models.citation import Citation
from src.domain.models.state import ResearchState
from src.graph.workflow import QueryWorkflow


@dataclass(slots=True)
class AgenticQaService:
    workflow: QueryWorkflow
    top_k: int = 6

    @classmethod
    def from_settings(cls, settings: Settings) -> "AgenticQaService":
        return cls(
            workflow=QueryWorkflow.from_settings(settings),
            top_k=settings.qa_top_k,
        )

    def answer(self, query: str, top_k: int | None = None, tables_only: bool = False) -> dict:
        resolved_top_k = top_k or self.top_k
        initial_state: ResearchState = {
            "user_query": query,
            "retry_count": 0,
            "max_retry_count": 2,
            "retrieval_plan": {
                "top_k": resolved_top_k,
                "tables_only": tables_only,
            },
        }
        final_state = self.workflow.run(initial_state)
        selected_evidence = list(final_state.get("selected_evidence", []))
        citations = self._build_citations(
            citation_map=list(final_state.get("citation_map", [])),
            evidence=selected_evidence,
        )
        return {
            "query": query,
            "answer": final_state.get("draft_answer", ""),
            "confidence": final_state.get("confidence", "low"),
            "model": final_state.get("model"),
            "prompt_family": final_state.get("prompt_family"),
            "embedding_backend": final_state.get("embedding_backend", "unknown"),
            "retrieved_count": len(final_state.get("retrieved_candidates", [])),
            "citations": [asdict(citation) for citation in citations],
            "evidence": [self._serialize_evidence(item) for item in selected_evidence],
            "workflow_status": final_state.get("workflow_status"),
            "route_type": (final_state.get("route_decision") or {}).get("route_type"),
        }

    @staticmethod
    def _build_citations(citation_map: list[dict], evidence: list[dict]) -> list[Citation]:
        evidence_by_id = {
            item["chunk"].chunk_id: item["chunk"]
            for item in evidence
            if "chunk" in item
        }
        citations: list[Citation] = []
        seen_chunk_ids: set[str] = set()
        for claim in citation_map:
            for chunk_id in claim.get("chunk_ids", []):
                if chunk_id in seen_chunk_ids or chunk_id not in evidence_by_id:
                    continue
                chunk = evidence_by_id[chunk_id]
                citations.append(
                    Citation(
                        claim=claim["claim"],
                        doc_id=chunk.doc_id,
                        page_no=chunk.page_no,
                        chunk_id=chunk.chunk_id,
                        excerpt=chunk.text[:240],
                    )
                )
                seen_chunk_ids.add(chunk_id)
        return citations

    @staticmethod
    def _serialize_evidence(item: dict) -> dict:
        chunk = item["chunk"]
        return {
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "page_no": chunk.page_no,
            "chunk_type": chunk.chunk_type,
            "section_path": chunk.section_path,
            "score": float(item.get("score", 0.0)),
            "sources": sorted(item.get("sources", [])),
            "text": chunk.text,
        }
