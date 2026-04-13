"""Section-aware chunker implementation."""

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
            source_span={
                "merged_block_ids": [blocks[0].block_id, blocks[1].block_id],
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
        return Chunk(
            chunk_id=build_chunk_id(document.doc_id, block.page_no or 1, chunk_index),
            doc_id=document.doc_id,
            text=block.text,
            page_no=block.page_no or 1,
            chunk_type=block.type,
            section_path=block.section_path.copy(),
            metadata={
                "block_ids": [block.block_id],
                "page_no": block.page_no or 1,
                "section_path": block.section_path.copy(),
                "source_block_count": 1,
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
        text = "\n\n".join(block.text for block in blocks).strip()
        return Chunk(
            chunk_id=build_chunk_id(document.doc_id, page_no, chunk_index),
            doc_id=document.doc_id,
            text=text,
            page_no=page_no,
            chunk_type=chunk_type,
            section_path=section_path,
            metadata={
                "block_ids": [block.block_id for block in blocks],
                "page_no": page_no,
                "section_path": section_path,
                "source_block_count": len(blocks),
                "char_count": len(text),
            },
        )

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
