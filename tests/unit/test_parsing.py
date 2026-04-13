import unittest

from src.domain.models.document import Block, Document, Page
from src.parsing.cleaner import DocumentCleaner
from src.parsing.section_builder import SectionBuilder


class ParsingHelpersTest(unittest.TestCase):
    def test_cleaner_removes_noise_and_normalizes_text(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[
                Page(
                    page_no=1,
                    blocks=[
                        Block(block_id="b1", type="paragraph", text="  Page 1  "),
                        Block(
                            block_id="b2",
                            type="paragraph",
                            text="Hello   world\n\n\nnext line",
                        ),
                    ],
                )
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertEqual(len(cleaned.pages[0].blocks), 1)
        self.assertEqual(cleaned.pages[0].blocks[0].text, "Hello world\n\nnext line")

    def test_cleaner_removes_repeated_headers(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[
                Page(
                    page_no=1,
                    blocks=[
                        Block(block_id="b1", type="paragraph", text="行业研究 | 汽车行业"),
                        Block(block_id="b2", type="paragraph", text="正文第一页"),
                    ],
                ),
                Page(
                    page_no=2,
                    blocks=[
                        Block(block_id="b3", type="paragraph", text="行业研究 | 汽车行业"),
                        Block(block_id="b4", type="paragraph", text="正文第二页"),
                    ],
                ),
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertEqual(len(cleaned.pages[0].blocks), 1)
        self.assertEqual(cleaned.pages[0].blocks[0].text, "正文第一页")
        self.assertEqual(len(cleaned.pages[1].blocks), 1)
        self.assertEqual(cleaned.pages[1].blocks[0].text, "正文第二页")

    def test_section_builder_tracks_nested_numeric_headings(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[
                Page(
                    page_no=1,
                    blocks=[
                        Block(block_id="b1", type="heading", text="1 Overview"),
                        Block(block_id="b2", type="paragraph", text="Top level"),
                        Block(block_id="b3", type="heading", text="1.1 Detail"),
                        Block(block_id="b4", type="paragraph", text="Nested"),
                    ],
                )
            ],
        )

        enriched = SectionBuilder().apply(document)

        self.assertEqual(enriched.pages[0].blocks[1].section_path, ["1 Overview"])
        self.assertEqual(
            enriched.pages[0].blocks[3].section_path,
            ["1 Overview", "1.1 Detail"],
        )


if __name__ == "__main__":
    unittest.main()
