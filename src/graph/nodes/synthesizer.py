"""Synthesizer node placeholder."""

from src.domain.models.state import ResearchState


class SynthesizerNode:
    def run(self, state: ResearchState) -> ResearchState:
        state.setdefault("draft_answer", "")
        return state

