"""Retrieval strategist node placeholder."""

from src.domain.models.state import ResearchState


class RetrievalStrategistNode:
    def run(self, state: ResearchState) -> ResearchState:
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
        state["retry_count"] = int(state.get("retry_count", 0) or 0) + 1
        return state

