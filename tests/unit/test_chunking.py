import unittest

from src.chunking.chunker import SectionAwareChunker
from src.chunking.rules import ChunkingConfig
from src.domain.models.document import Block, Document, Page


class ChunkingTest(unittest.TestCase):
    def test_chunker_groups_blocks_within_same_section(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[
                Page(
                    page_no=1,
                    blocks=[
                        Block(
                            block_id="b1",
                            type="paragraph",
                            text="A" * 80,
                            page_no=1,
                            section_path=["1 Intro"],
                        ),
                        Block(
                            block_id="b2",
                            type="paragraph",
                            text="B" * 80,
                            page_no=1,
                            section_path=["1 Intro"],
                        ),
                        Block(
                            block_id="b3",
                            type="paragraph",
                            text="C" * 80,
                            page_no=1,
                            section_path=["2 Next"],
                        ),
                    ],
                )
            ],
        )

        chunker = SectionAwareChunker(
            ChunkingConfig(target_size=220, overlap=20, min_chunk_size=60)
        )
        chunks = chunker.chunk(document)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].section_path, ["1 Intro"])
        self.assertEqual(chunks[0].metadata["source_block_count"], 2)
        self.assertEqual(chunks[1].section_path, ["2 Next"])


if __name__ == "__main__":
    unittest.main()
