"""Generic Chinese QA prompt template."""

from __future__ import annotations

from src.generation.prompts.base import BasePromptTemplate, PromptBundle


class ChineseGenericPromptTemplate(BasePromptTemplate):
    family = "zh_generic"

    def build(self, query: str, evidence: list[dict]) -> PromptBundle:
        context = _format_evidence(evidence)
        return PromptBundle(
            system_prompt=(
                "你是一个基于 PDF 证据进行问答的助手。"
                "你只能依据给定证据回答，不能编造事实。"
                "如果证据不足，请明确说明“根据当前证据无法确定”。"
                "回答要简洁、准确、克制，并优先使用中文。"
            ),
            user_prompt=(
                f"问题：\n{query}\n\n"
                f"证据：\n{context}\n\n"
                "请基于上述证据回答。\n"
                "要求：\n"
                "1. 只能使用证据中的信息。\n"
                "2. 如果证据不足，直接说明无法确定，不要猜测。\n"
                "3. 尽量先给结论，再补充必要说明。"
            ),
        )


def _format_evidence(evidence: list[dict]) -> str:
    lines: list[str] = []
    for idx, item in enumerate(evidence, start=1):
        chunk = item["chunk"]
        label = f"C{idx}"
        section = " > ".join(chunk.section_path) if chunk.section_path else "未命名章节"
        lines.append(
            f"[{label}] doc_id={chunk.doc_id} page={chunk.page_no} "
            f"type={chunk.chunk_type} section={section}\n{chunk.text.strip()}"
        )
    return "\n\n".join(lines)
