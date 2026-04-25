"""Synthesizer node backed by the existing answer generation stack."""

from __future__ import annotations

import logging

from src.config.settings import Settings
from src.domain.models.state import ResearchState
from src.generation.answer_generator import AnswerGenerator
from src.generation.factory import create_llm_provider
from src.generation.prompts.factory import create_prompt_template
from src.retrieval.context_packer import ContextPacker

logger = logging.getLogger(__name__)


class SynthesizerNode:
    def __init__(
        self,
        answer_generator: AnswerGenerator | None = None,
        context_packer: ContextPacker | None = None,
        default_top_k: int = 6,
        strict: bool = False,
    ) -> None:
        self.answer_generator = answer_generator
        self.context_packer = context_packer or ContextPacker()
        self.default_top_k = default_top_k
        self.strict = strict

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
            strict=True,
        )

    def run(self, state: ResearchState) -> ResearchState:
        if self.answer_generator is None:
            if self.strict:
                raise RuntimeError("SynthesizerNode requires an AnswerGenerator in strict mode.")
            state.setdefault("draft_answer", "placeholder draft answer")
            state.setdefault(
                "claims",
                [{"claim": "placeholder claim", "supporting_chunk_ids": ["placeholder_chunk"]}],
            )
            state.setdefault("confidence", "medium")
            logger.info(
                "synthesizer.placeholder evidence=%s claims=%s confidence=%s",
                len(state.get("selected_evidence", [])),
                len(state.get("claims", [])),
                state.get("confidence"),
            )
            return state

        query = (state.get("normalized_query") or state.get("user_query") or "").strip()
        retrieval_plan = state.get("retrieval_plan", {}) or {}
        generation_query = self._build_generation_query(
            query=query,
            retrieval_plan=retrieval_plan,
        )
        conversation_context = self._build_conversation_context(
            retrieval_plan,
            conversation_summary=str(state.get("conversation_summary", "") or ""),
        )
        max_items = int(retrieval_plan.get("top_k", self.default_top_k))
        selected_evidence = list(state.get("selected_evidence", []))
        packed_evidence = self.context_packer.pack(selected_evidence, max_items=max_items)
        state["generation_query"] = generation_query
        state["generation_context"] = dict(conversation_context)
        logger.info(
            "synthesizer.start query=%r generation_query=%r conversation_context=%s selected=%s packed=%s evidence_types=%s",
            query,
            generation_query,
            conversation_context,
            len(selected_evidence),
            len(packed_evidence),
            state.get("selected_evidence_types", []),
        )
        generation = self.answer_generator.generate(
            query=query,
            evidence=packed_evidence,
            conversation_context=conversation_context,
        )
        state["draft_answer"] = generation["answer"]
        state["claims"] = generation.get("claims", [])
        state["confidence"] = generation.get("confidence", state.get("confidence", "low"))
        if generation.get("model"):
            state["model"] = generation["model"]
        if generation.get("prompt_family"):
            state["prompt_family"] = generation["prompt_family"]
        state["next_action"] = "citation_auditor"
        logger.info(
            "synthesizer.result answer_len=%s claims=%s confidence=%s model=%s prompt_family=%s",
            len(state["draft_answer"]),
            len(state["claims"]),
            state["confidence"],
            state.get("model"),
            state.get("prompt_family"),
        )
        return state

    @staticmethod
    def _build_generation_query(query: str, retrieval_plan: dict) -> str:
        normalized_query = " ".join(str(query or "").strip().split())
        enrichment_terms: list[str] = []

        for term in retrieval_plan.get("dialogue_referents", []) or []:
            normalized = str(term).strip()
            if normalized and normalized not in normalized_query and normalized not in enrichment_terms:
                enrichment_terms.append(normalized)

        comparison_target = str(retrieval_plan.get("comparison_target", "")).strip()
        if comparison_target and comparison_target not in normalized_query and comparison_target not in enrichment_terms:
            enrichment_terms.append(comparison_target)

        output_style = str(retrieval_plan.get("output_style", "")).strip()
        if output_style and output_style not in normalized_query and output_style not in enrichment_terms:
            enrichment_terms.append(output_style)

        if enrichment_terms:
            return " ".join([normalized_query, *enrichment_terms]).strip()
        return normalized_query

    @staticmethod
    def _build_conversation_context(
        retrieval_plan: dict,
        conversation_summary: str = "",
    ) -> dict[str, object]:
        context: dict[str, object] = {}
        carry_over_constraints = retrieval_plan.get("carry_over_constraints", {})
        if isinstance(carry_over_constraints, dict) and carry_over_constraints.get("follow_up"):
            context["follow_up"] = True

        dialogue_referents = retrieval_plan.get("dialogue_referents", [])
        if isinstance(dialogue_referents, list) and dialogue_referents:
            context["dialogue_referents"] = [str(item) for item in dialogue_referents if str(item).strip()]

        comparison_target = str(retrieval_plan.get("comparison_target", "")).strip()
        if comparison_target:
            context["comparison_target"] = comparison_target

        output_style = str(retrieval_plan.get("output_style", "")).strip()
        if output_style:
            context["output_style"] = output_style

        normalized_summary = str(retrieval_plan.get("conversation_summary", "")).strip() or str(conversation_summary).strip()
        if normalized_summary:
            context["conversation_summary"] = normalized_summary

        if context.get("dialogue_referents") or comparison_target:
            context["dialogue_mode"] = "compare"
        elif context.get("follow_up"):
            context["dialogue_mode"] = "follow_up"
        else:
            context["dialogue_mode"] = "single_turn"

        return context

