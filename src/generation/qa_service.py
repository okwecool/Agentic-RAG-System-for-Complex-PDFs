"""Question answering orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from src.config.settings import Settings
from src.generation.answer_generator import AnswerGenerator
from src.generation.citation_auditor import CitationAuditor
from src.generation.factory import create_llm_provider
from src.generation.prompts.factory import create_prompt_template
from src.generation.response_builder import build_citations, serialize_citations, serialize_evidence_list
from src.retrieval.context_packer import ContextPacker
from src.retrieval.factory import create_hybrid_fusion, create_reranker
from src.retrieval.search_service import SearchService

logger = logging.getLogger(__name__)


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
        prompt_template = create_prompt_template(settings)
        return cls(
            search_service=search_service,
            answer_generator=AnswerGenerator(
                llm_provider=llm_provider,
                prompt_template=prompt_template,
            ),
            citation_auditor=CitationAuditor(),
            context_packer=ContextPacker(),
            top_k=settings.qa_top_k,
        )

    def answer(
        self,
        query: str,
        top_k: int | None = None,
        tables_only: bool = False,
        session_id: str | None = None,
    ) -> dict:
        resolved_top_k = top_k or self.top_k
        logger.info(
            "qa.start query=%r top_k=%s tables_only=%s",
            query,
            resolved_top_k,
            tables_only,
        )
        retrieved = (
            self.search_service.search_tables(query, top_k=resolved_top_k)
            if tables_only
            else self.search_service.search_chunks(query, top_k=resolved_top_k)
        )
        packed = self.context_packer.pack(retrieved, max_items=resolved_top_k)
        logger.info(
            "qa.context retrieved=%s packed=%s",
            len(retrieved),
            len(packed),
        )
        generation = self.answer_generator.generate(query=query, evidence=packed)
        audit = self.citation_auditor.audit(generation["claims"], packed)
        citations = build_citations(audit.get("verified_claims", []), packed)
        logger.info(
            "qa.finish confidence=%s citations=%s model=%s",
            audit.get("final_confidence", generation.get("confidence", "low")),
            len(citations),
            generation.get("model"),
        )
        return {
            "query": query,
            "answer": generation["answer"],
            "confidence": audit.get("final_confidence", generation.get("confidence", "low")),
            "model": generation.get("model"),
            "prompt_family": generation.get("prompt_family"),
            "embedding_backend": self.search_service.embedding_backend,
            "retrieved_count": len(retrieved),
            "citations": serialize_citations(citations),
            "evidence": serialize_evidence_list(packed),
        }


def _create_search_service(settings: Settings) -> SearchService:
    fusion = create_hybrid_fusion(settings)
    reranker = create_reranker(settings)
    logger.info(
        "qa.init retrieval_index_dir=%s chunks_dir=%s embedding_model_dir=%s fusion=%s reranker=%s",
        settings.retrieval_index_dir,
        settings.chunks_dir,
        settings.local_embedding_model_dir,
        fusion.describe(),
        reranker.describe() if hasattr(reranker, "describe") else getattr(reranker, "backend", "unknown"),
    )
    if settings.retrieval_index_dir and settings.retrieval_index_dir.exists():
        return SearchService.from_persisted_index(
            index_dir=settings.retrieval_index_dir,
            embedding_model_path=str(settings.local_embedding_model_dir)
            if settings.local_embedding_model_dir
            else None,
            fusion=fusion,
            reranker=reranker,
        )
    return SearchService.from_chunk_artifacts(
        chunks_dir=settings.chunks_dir,
        embedding_model_path=str(settings.local_embedding_model_dir)
        if settings.local_embedding_model_dir
        else None,
        fusion=fusion,
        reranker=reranker,
    )
