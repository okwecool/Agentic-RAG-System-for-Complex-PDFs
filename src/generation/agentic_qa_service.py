"""Agentic QA service built on top of QueryWorkflow."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import logging
from uuid import uuid4

from src.config.settings import Settings
from src.domain.models.citation import Citation
from src.domain.models.state import ResearchState
from src.graph.workflow import QueryWorkflow
from src.memory.summarizer import ConversationSummarizer
from src.memory.thread_store import InMemoryThreadStore

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgenticQaService:
    workflow: QueryWorkflow
    thread_store: InMemoryThreadStore
    summarizer: ConversationSummarizer
    top_k: int = 6

    @classmethod
    def from_settings(cls, settings: Settings) -> "AgenticQaService":
        return cls(
            workflow=QueryWorkflow.from_settings(settings),
            thread_store=InMemoryThreadStore(),
            summarizer=ConversationSummarizer(),
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
        resolved_session_id = (session_id or "").strip() or uuid4().hex
        session_state = self.thread_store.get(resolved_session_id)
        turn_index = int(session_state.get("turn_index", 0) or 0) + 1
        logger.info(
            "agentic_qa.start query=%r top_k=%s tables_only=%s session_id=%s turn_index=%s",
            query,
            resolved_top_k,
            tables_only,
            resolved_session_id,
            turn_index,
        )
        initial_state: ResearchState = {
            "session_id": resolved_session_id,
            "thread_id": resolved_session_id,
            "turn_index": turn_index,
            "messages": list(session_state.get("messages", [])),
            "conversation_summary": session_state.get("conversation_summary", ""),
            "current_entities": dict(session_state.get("current_entities", {})),
            "user_query": query,
            "retry_count": 0,
            "max_retry_count": 2,
            "request_options": {
                "top_k": resolved_top_k,
                "tables_only": tables_only,
            },
        }
        final_state = self.workflow.run(initial_state)
        logger.info(
            "agentic_qa.finish workflow_status=%s route_type=%s retrieved=%s selected=%s confidence=%s model=%s trace_len=%s",
            final_state.get("workflow_status"),
            (final_state.get("route_decision") or {}).get("route_type"),
            len(final_state.get("retrieved_candidates", [])),
            len(final_state.get("selected_evidence", [])),
            final_state.get("confidence"),
            final_state.get("model"),
            len(final_state.get("route_trace", [])),
        )
        selected_evidence = list(final_state.get("selected_evidence", []))
        citations = self._build_citations(
            citation_map=list(final_state.get("citation_map", [])),
            evidence=selected_evidence,
        )
        result = {
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
            "route_trace": list(final_state.get("route_trace", [])),
        }
        persisted_state = self._build_persisted_state(
            previous_state=session_state,
            final_state=final_state,
            answer_text=result["answer"],
        )
        self.thread_store.put(resolved_session_id, persisted_state)
        result["session_id"] = resolved_session_id
        result["turn_index"] = persisted_state.get("turn_index", turn_index)
        result["conversation_summary"] = persisted_state.get("conversation_summary", "")
        return result

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

    def _build_persisted_state(
        self,
        previous_state: ResearchState,
        final_state: ResearchState,
        answer_text: str,
    ) -> ResearchState:
        messages = list(previous_state.get("messages", []))
        messages.append({"role": "user", "content": final_state.get("user_query", "")})
        messages.append({"role": "assistant", "content": answer_text})
        turn_index = int(final_state.get("turn_index", previous_state.get("turn_index", 0)) or 0)
        current_entities = dict(final_state.get("current_entities", {}))
        if not current_entities:
            current_entities = dict(previous_state.get("current_entities", {}))
        extracted = current_entities.get("current_query_entities") or []
        if extracted:
            current_entities["last_entity"] = extracted[0]
        elif current_entities.get("conversation_anchor"):
            current_entities["last_entity"] = current_entities["conversation_anchor"]

        return {
            "session_id": str(final_state.get("session_id") or previous_state.get("session_id") or ""),
            "thread_id": str(final_state.get("thread_id") or previous_state.get("thread_id") or ""),
            "turn_index": turn_index,
            "messages": messages[-20:],
            "conversation_summary": self.summarizer.summarize(messages),
            "current_entities": current_entities,
            "current_domain": str(final_state.get("current_domain", previous_state.get("current_domain", ""))),
        }
