"""Question answering orchestration service."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass

from src.config.settings import Settings
from src.domain.models.citation import Citation
from src.generation.answer_generator import AnswerGenerator
from src.generation.citation_auditor import CitationAuditor
from src.generation.factory import create_llm_provider
from src.retrieval.context_packer import ContextPacker
from src.retrieval.search_service import SearchService


@dataclass(slots=True)
class QaService:
    search_service: SearchService
    answer_generator: AnswerGenerator
    citation_auditor: CitationAuditor
    context_packer: ContextPacker
    top_k: int = 6

    @classmethod
    def from_settings(cls, settings: Settings) -> "QaService":
        search_service = _create_search_service(settings)
        llm_provider = create_llm_provider(settings)
        return cls(
            search_service=search_service,
            answer_generator=AnswerGenerator(llm_provider=llm_provider),
            citation_auditor=CitationAuditor(),
            context_packer=ContextPacker(),
            top_k=settings.qa_top_k,
        )

    def answer(self, query: str, top_k: int | None = None, tables_only: bool = False) -> dict:
        resolved_top_k = top_k or self.top_k
        retrieved = (
            self.search_service.search_tables(query, top_k=resolved_top_k)
            if tables_only
            else self.search_service.search_chunks(query, top_k=resolved_top_k)
        )
        packed = self.context_packer.pack(retrieved, max_items=resolved_top_k)
        generation = self.answer_generator.generate(query=query, evidence=packed)
        audit = self.citation_auditor.audit(generation["claims"], packed)
        citations = self._build_citations(audit.get("verified_claims", []), packed)
        return {
            "query": query,
            "answer": generation["answer"],
            "confidence": audit.get("final_confidence", generation.get("confidence", "low")),
            "model": generation.get("model"),
            "embedding_backend": self.search_service.embedding_backend,
            "retrieved_count": len(retrieved),
            "citations": [asdict(citation) for citation in citations],
            "evidence": [self._serialize_evidence(item) for item in packed],
        }

    @staticmethod
    def _build_citations(verified_claims: list[dict], evidence: list[dict]) -> list[Citation]:
        evidence_by_id = {item["chunk"].chunk_id: item["chunk"] for item in evidence if "chunk" in item}
        citations: list[Citation] = []
        seen_chunk_ids: set[str] = set()
        for claim in verified_claims:
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


def _create_search_service(settings: Settings) -> SearchService:
    if settings.retrieval_index_dir and settings.retrieval_index_dir.exists():
        return SearchService.from_persisted_index(
            index_dir=settings.retrieval_index_dir,
            embedding_model_path=str(settings.local_embedding_model_dir)
            if settings.local_embedding_model_dir
            else None,
        )
    return SearchService.from_chunk_artifacts(
        chunks_dir=settings.chunks_dir,
        embedding_model_path=str(settings.local_embedding_model_dir)
        if settings.local_embedding_model_dir
        else None,
    )
