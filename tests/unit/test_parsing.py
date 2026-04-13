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
                        Block(block_id="b1", type="paragraph", text="Report Header"),
                        Block(block_id="b2", type="paragraph", text="First page body"),
                    ],
                ),
                Page(
                    page_no=2,
                    blocks=[
                        Block(block_id="b3", type="paragraph", text="Report Header"),
                        Block(block_id="b4", type="paragraph", text="Second page body"),
                    ],
                ),
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertEqual(len(cleaned.pages[0].blocks), 1)
        self.assertEqual(cleaned.pages[0].blocks[0].text, "First page body")
        self.assertEqual(len(cleaned.pages[1].blocks), 1)
        self.assertEqual(cleaned.pages[1].blocks[0].text, "Second page body")

    def test_cleaner_merges_wrapped_non_heading_lines(self) -> None:
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
                            type="heading",
                            text="This is a wrapped body line that should not be a heading",
                            bbox=(80, 100, 500, 114),
                            page_no=1,
                        ),
                        Block(
                            block_id="b2",
                            type="heading",
                            text="because it is just the next line of the same paragraph",
                            bbox=(80, 118, 500, 132),
                            page_no=1,
                        ),
                    ],
                )
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertEqual(len(cleaned.pages[0].blocks), 1)
        self.assertEqual(cleaned.pages[0].blocks[0].type, "paragraph")
        self.assertIn("same paragraph", cleaned.pages[0].blocks[0].text)

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
