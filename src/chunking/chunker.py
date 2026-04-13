"""Section-aware chunker skeleton."""

from src.domain.models.document import Chunk, Document
from src.utils.ids import build_chunk_id


class SectionAwareChunker:
    def chunk(self, document: Document) -> list[Chunk]:
        chunks: list[Chunk] = []
        for page in document.pages:
            for index, block in enumerate(page.blocks, start=1):
                chunks.append(
                    Chunk(
                        chunk_id=build_chunk_id(document.doc_id, page.page_no, index),
                        doc_id=document.doc_id,
                        text=block.text,
                        page_no=page.page_no,
                        chunk_type=block.type,
                        section_path=block.section_path.copy(),
                        metadata={"block_id": block.block_id},
                    )
                )
        return chunks

