"""Section-aware chunker implementation."""

import re

from src.chunking.rules import ChunkingConfig
from src.domain.models.document import Block, Chunk, Document
from src.utils.ids import build_chunk_id


class SectionAwareChunker:
    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig()

    def chunk(self, document: Document) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 0
        pending_blocks: list[Block] = []
        current_section: tuple[str, ...] | None = None
        current_page: int | None = None

        for page in document.pages:
            for block in page.blocks:
                if not block.text.strip():
                    continue
                if block.type in {"table", "figure_caption"}:
                    if pending_blocks:
                        chunk_index, built = self._flush_pending(
                            document=document,
                            pending_blocks=pending_blocks,
                            chunk_index=chunk_index,
                        )
                        chunks.extend(built)
                        pending_blocks = []
                    chunk_index += 1
                    chunks.append(self._build_single_block_chunk(document, block, chunk_index))
                    current_section = None
                    current_page = None
                    continue

                block_section = tuple(block.section_path)
                block_page = page.page_no
                if (
                    pending_blocks
                    and (block_section != current_section or block_page != current_page)
                ):
                    chunk_index, built = self._flush_pending(
                        document=document,
                        pending_blocks=pending_blocks,
                        chunk_index=chunk_index,
                    )
                    chunks.extend(built)
                    pending_blocks = []

                current_section = block_section
                current_page = block_page
                pending_blocks.append(block)

        if pending_blocks:
            chunk_index, built = self._flush_pending(
                document=document,
                pending_blocks=pending_blocks,
                chunk_index=chunk_index,
            )
            chunks.extend(built)

        return chunks

    def _flush_pending(
        self,
        document: Document,
        pending_blocks: list[Block],
        chunk_index: int,
    ) -> tuple[int, list[Chunk]]:
        if not pending_blocks:
            return chunk_index, []

        pending_blocks = self._merge_heading_prefix(pending_blocks)
        chunks: list[Chunk] = []
        text_parts: list[str] = []
        source_blocks: list[Block] = []

        for block in pending_blocks:
            candidate_parts = text_parts + [block.text]
            candidate_text = "\n\n".join(candidate_parts).strip()
            if (
                text_parts
                and len(candidate_text) > self.config.target_size
                and len("\n\n".join(text_parts).strip()) >= self.config.min_chunk_size
            ):
                chunk_index += 1
                chunks.append(
                    self._build_chunk(
                        document=document,
                        blocks=source_blocks,
                        chunk_index=chunk_index,
                    )
                )
                text_parts = self._build_overlap_tail(text_parts)
                source_blocks = []
            text_parts.append(block.text)
            source_blocks.append(block)

        if source_blocks:
            chunk_index += 1
            chunks.append(
                self._build_chunk(
                    document=document,
                    blocks=source_blocks,
                    chunk_index=chunk_index,
                )
            )

        return chunk_index, chunks

    def _merge_heading_prefix(self, blocks: list[Block]) -> list[Block]:
        if len(blocks) < 2:
            return blocks
        if blocks[0].type != "heading":
            return blocks
        if len(blocks[0].text.strip()) > 40:
            return blocks
        merged_text = f"{blocks[0].text.strip()}\n\n{blocks[1].text.strip()}".strip()
        merged_first = Block(
            block_id=f"{blocks[0].block_id}+{blocks[1].block_id}",
            type=blocks[1].type,
            text=merged_text,
            bbox=blocks[1].bbox,
            section_path=blocks[1].section_path.copy(),
            page_no=blocks[1].page_no,
            table_html=blocks[1].table_html,
            table_json=blocks[1].table_json,
            content_role=blocks[1].content_role or "narrative_paragraph",
            source_span={
                "merged_block_ids": [blocks[0].block_id, blocks[1].block_id],
                "merged_content_roles": [
                    blocks[0].content_role or blocks[0].type,
                    blocks[1].content_role or blocks[1].type,
                ],
                "page_no": blocks[1].page_no,
            },
        )
        return [merged_first, *blocks[2:]]

    def _build_single_block_chunk(
        self,
        document: Document,
        block: Block,
        chunk_index: int,
    ) -> Chunk:
        evidence_type = self._infer_evidence_type([block], document)
        return Chunk(
            chunk_id=build_chunk_id(document.doc_id, block.page_no or 1, chunk_index),
            doc_id=document.doc_id,
            text=block.text,
            page_no=block.page_no or 1,
            chunk_type=block.type,
            section_path=block.section_path.copy(),
            evidence_type=evidence_type,
            metadata={
                "block_ids": [block.block_id],
                "page_no": block.page_no or 1,
                "section_path": block.section_path.copy(),
                "source_block_count": 1,
                "source_roles": [block.content_role or block.type],
                "source_page_profile": (block.source_span or {}).get("page_profile"),
                "document_source_type": document.document_source_type,
                "evidence_type": evidence_type,
            },
        )

    def _build_chunk(
        self,
        document: Document,
        blocks: list[Block],
        chunk_index: int,
    ) -> Chunk:
        page_no = blocks[0].page_no or 1
        section_path = blocks[0].section_path.copy()
        chunk_type = "mixed" if len({block.type for block in blocks}) > 1 else blocks[0].type
        text = self._compose_chunk_text(blocks)
        evidence_type = self._infer_evidence_type(blocks, document)
        source_roles = self._collect_source_roles(blocks)
        source_page_profile = self._resolve_source_page_profile(blocks)
        return Chunk(
            chunk_id=build_chunk_id(document.doc_id, page_no, chunk_index),
            doc_id=document.doc_id,
            text=text,
            page_no=page_no,
            chunk_type=chunk_type,
            section_path=section_path,
            evidence_type=evidence_type,
            metadata={
                "block_ids": [block.block_id for block in blocks],
                "page_no": page_no,
                "section_path": section_path,
                "source_block_count": len(blocks),
                "char_count": len(text),
                "source_roles": source_roles,
                "source_page_profile": source_page_profile,
                "document_source_type": document.document_source_type,
                "evidence_type": evidence_type,
            },
        )

    def _compose_chunk_text(self, blocks: list[Block]) -> str:
        if not blocks:
            return ""
        parts = [blocks[0].text.strip()]
        for previous, current in zip(blocks, blocks[1:]):
            separator = self._block_separator(previous, current)
            parts.append(separator)
            parts.append(current.text.strip())
        return "".join(parts).strip()

    def _block_separator(self, previous: Block, current: Block) -> str:
        previous_text = previous.text.strip()
        current_text = current.text.strip()
        if not previous_text or not current_text:
            return ""
        if previous.type == "heading" and current.type != "heading":
            return "\n\n"
        if current.type == "list_item":
            return "\n\n"
        if self._looks_like_wrapped_continuation(previous_text, current_text):
            return self._inline_separator(previous_text, current_text)
        return "\n\n"

    @staticmethod
    def _looks_like_wrapped_continuation(previous_text: str, current_text: str) -> bool:
        if not previous_text or not current_text:
            return False
        if previous_text.endswith(("。", "！", "？", "；", "：", ".", "!", "?", ";", ":")):
            return False
        if previous_text.startswith(("图表", "图：", "表头:", "数据:")):
            return False
        if current_text.startswith(("图表", "表头:", "数据:", "•", "◼", "◆", "➢")):
            return False
        return True

    @staticmethod
    def _inline_separator(previous_text: str, current_text: str) -> str:
        if re.search(r"[A-Za-z0-9]$", previous_text) and re.match(r"^[A-Za-z0-9]", current_text):
            return " "
        if previous_text.endswith(("(", "（", "[", "【", "“", "\"", "'")):
            return ""
        if current_text.startswith((")", "）", "]", "】", "”", "\"", "'", "，", "。", "！", "？", "；", "：", ",", ".", "!", "?", ";", ":")):
            return ""
        return ""

    def _build_overlap_tail(self, text_parts: list[str]) -> list[str]:
        if self.config.overlap <= 0:
            return []
        collected: list[str] = []
        current_length = 0
        for part in reversed(text_parts):
            collected.insert(0, part)
            current_length += len(part)
            if current_length >= self.config.overlap:
                break
        return collected

    @staticmethod
    def _collect_source_roles(blocks: list[Block]) -> list[str]:
        roles: list[str] = []
        for block in blocks:
            merged_roles = (block.source_span or {}).get("merged_content_roles", [])
            if merged_roles:
                roles.extend(str(role) for role in merged_roles if role)
            else:
                roles.append(block.content_role or block.type)
        return sorted(dict.fromkeys(roles))

    @staticmethod
    def _resolve_source_page_profile(blocks: list[Block]) -> str | None:
        for block in blocks:
            page_profile = (block.source_span or {}).get("page_profile")
            if page_profile:
                return str(page_profile)
        return None

    def _infer_evidence_type(self, blocks: list[Block], document: Document) -> str:
        roles = self._collect_source_roles(blocks)
        page_profile = self._resolve_source_page_profile(blocks)
        if "table" in roles:
            return "table_evidence"
        if any(role in {"figure_caption", "table_caption"} for role in roles):
            return "caption_evidence"
        if page_profile == "label_dense" and all(
            role in {"chart_label", "heading", "figure_caption"} for role in roles
        ):
            return "chart_evidence"
        if all(role in {"heading", "source_note"} for role in roles):
            return "navigational_evidence"
        if "source_note" in roles:
            return "low_value_evidence"
        if document.document_source_type == "table_corpus":
            return "table_evidence"
        return "narrative_evidence"
