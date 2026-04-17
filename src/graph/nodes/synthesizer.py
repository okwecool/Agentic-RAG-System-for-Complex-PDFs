"""Synthesizer node backed by the existing answer generation stack."""

from __future__ import annotations

from src.config.settings import Settings
from src.domain.models.state import ResearchState
from src.generation.answer_generator import AnswerGenerator
from src.generation.factory import create_llm_provider
from src.generation.prompts.factory import create_prompt_template
from src.retrieval.context_packer import ContextPacker


class SynthesizerNode:
    def __init__(
        self,
        answer_generator: AnswerGenerator | None = None,
        context_packer: ContextPacker | None = None,
        default_top_k: int = 6,
    ) -> None:
        self.answer_generator = answer_generator
        self.context_packer = context_packer or ContextPacker()
        self.default_top_k = default_top_k

    @classmethod
    def from_settings(cls, settings: Settings) -> "SynthesizerNode":
        llm_provider = create_llm_provider(settings)
        prompt_template = create_prompt_template(settings)
        return cls(
            answer_generator=AnswerGenerator(
                llm_provider=llm_provider,
                prompt_template=prompt_template,
            ),
            context_packer=ContextPacker(),
            default_top_k=settings.qa_top_k,
        )

    def run(self, state: ResearchState) -> ResearchState:
        if self.answer_generator is None:
            state.setdefault("draft_answer", "placeholder draft answer")
            state.setdefault(
                "claims",
                [{"claim": "placeholder claim", "supporting_chunk_ids": ["placeholder_chunk"]}],
            )
            state.setdefault("confidence", "medium")
            return state

        query = (state.get("normalized_query") or state.get("user_query") or "").strip()
        max_items = int(state.get("retrieval_plan", {}).get("top_k", self.default_top_k))
        selected_evidence = list(state.get("selected_evidence", []))
        packed_evidence = self.context_packer.pack(selected_evidence, max_items=max_items)
        generation = self.answer_generator.generate(query=query, evidence=packed_evidence)
        state["draft_answer"] = generation["answer"]
        state["claims"] = generation.get("claims", [])
        state["confidence"] = generation.get("confidence", state.get("confidence", "low"))
        state["next_action"] = "citation_auditor"
        return state

