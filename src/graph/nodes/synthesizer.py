"""Synthesizer node placeholder."""

from src.domain.models.state import ResearchState


class SynthesizerNode:
    def run(self, state: ResearchState) -> ResearchState:
        state.setdefault("draft_answer", "placeholder draft answer")
        state.setdefault(
            "claims",
            [{"claim": "placeholder claim", "chunk_ids": ["placeholder_chunk"]}],
        )
        state.setdefault("confidence", "medium")
        return state

