"""Answer generation built on top of pluggable LLM providers."""

from __future__ import annotations

from src.domain.protocols.llm import LlmProvider


class AnswerGenerator:
    def __init__(self, llm_provider: LlmProvider) -> None:
        self.llm_provider = llm_provider

    def generate(self, query: str, evidence: list[dict]) -> dict:
        if not evidence:
            return {
                "answer": "I could not find enough supporting evidence in the indexed PDFs.",
                "claims": [],
                "confidence": "low",
                "model": self.llm_provider.model_name,
            }

        prompt = self._build_user_prompt(query=query, evidence=evidence)
        answer = self.llm_provider.generate(
            system_prompt=(
                "You answer questions using only the provided PDF evidence. "
                "Be concise, avoid unsupported claims, and explicitly mention uncertainty "
                "when the evidence is incomplete."
            ),
            user_prompt=prompt,
        )
        supporting_chunk_ids = [
            item["chunk"].chunk_id for item in evidence if "chunk" in item
        ]
        return {
            "answer": answer,
            "claims": [
                {
                    "claim": answer,
                    "supporting_chunk_ids": supporting_chunk_ids,
                }
            ],
            "confidence": "medium" if supporting_chunk_ids else "low",
            "model": self.llm_provider.model_name,
        }

    @staticmethod
    def _build_user_prompt(query: str, evidence: list[dict]) -> str:
        context_lines = []
        for idx, item in enumerate(evidence, start=1):
            chunk = item["chunk"]
            label = f"C{idx}"
            section = " > ".join(chunk.section_path) if chunk.section_path else "N/A"
            context_lines.append(
                f"[{label}] doc_id={chunk.doc_id} page={chunk.page_no} "
                f"type={chunk.chunk_type} section={section}\n{chunk.text.strip()}"
            )
        context = "\n\n".join(context_lines)
        return (
            f"Question:\n{query}\n\n"
            "Evidence:\n"
            f"{context}\n\n"
            "Write a concise answer in Chinese. If the evidence is insufficient, say so clearly."
        )
