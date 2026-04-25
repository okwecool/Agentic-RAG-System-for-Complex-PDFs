"""Generic Chinese QA prompt template."""

from __future__ import annotations

from src.generation.prompts.base import BasePromptTemplate, PromptBundle


class ChineseGenericPromptTemplate(BasePromptTemplate):
    family = "zh_generic"

    def build(
        self,
        query: str,
        evidence: list[dict],
        conversation_context: dict | None = None,
    ) -> PromptBundle:
        context = _format_evidence(evidence)
        conversation_block = _format_conversation_context(conversation_context)
        return PromptBundle(
            system_prompt=(
                "你是一个基于 PDF 证据进行问答的助手。"
                "你只能依据给定证据回答，不能编造事实。"
                "如果证据不足，请明确说明“根据当前证据无法确定”。"
                "回答要简洁、准确、克制，并优先使用中文。"
            ),
            user_prompt=(
                f"问题：\n{query}\n\n"
                f"{conversation_block}"
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


def _format_conversation_context(conversation_context: dict | None) -> str:
    if not conversation_context:
        return ""

    lines: list[str] = []

    dialogue_referents = conversation_context.get("dialogue_referents", [])
    if isinstance(dialogue_referents, list) and dialogue_referents:
        lines.append(f"对话上下文-关联实体：{', '.join(str(item) for item in dialogue_referents)}")

    comparison_target = str(conversation_context.get("comparison_target", "")).strip()
    if comparison_target:
        lines.append(f"对话上下文-比较对象：{comparison_target}")

    output_style = str(conversation_context.get("output_style", "")).strip()
    if output_style:
        lines.append(f"对话上下文-输出风格：{output_style}")

    conversation_summary = str(conversation_context.get("conversation_summary", "")).strip()
    if conversation_summary:
        lines.append(f"会话摘要：{conversation_summary}")

    dialogue_mode = str(conversation_context.get("dialogue_mode", "")).strip()
    follow_up = bool(conversation_context.get("follow_up"))
    if follow_up:
        lines.append("这是一个承接上轮上下文的问题，请沿用上轮已确定的主体和分析口径。")
    if dialogue_mode == "compare":
        lines.append("请按对比方式组织答案，明确区分不同主体，不要把前者后者答混。")

    if output_style == "list":
        lines.append("请使用列表形式作答，按要点分条给出。")
    elif output_style == "detailed":
        lines.append("请先给结论，再展开说明关键依据和差异点。")

    if not lines:
        return ""
    return "\n".join(lines) + "\n\n"
