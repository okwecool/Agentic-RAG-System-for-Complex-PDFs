import unittest

from src.domain.models.document import Block, Document, Page
from src.parsing.table_extractor import TableExtractor


class FakeTable:
    def __init__(self, bbox, rows) -> None:
        self.bbox = bbox
        self._rows = rows

    def extract(self):
        return self._rows


class FakeTableFinder:
    def __init__(self, tables) -> None:
        self.tables = tables


class FakePdfPage:
    def __init__(self, tables, width=600, height=800) -> None:
        self._tables = tables
        self.rect = type("Rect", (), {"width": width, "height": height})()

    def find_tables(self):
        return FakeTableFinder(self._tables)


class FakePdfDocument:
    def __init__(self, pages) -> None:
        self._pages = pages

    def __getitem__(self, index):
        return self._pages[index]

    def close(self):
        return None


class FakeFitz:
    def __init__(self, pages) -> None:
        self._pages = pages

    def open(self, source_file):
        del source_file
        return FakePdfDocument(self._pages)


class TableExtractorTest(unittest.TestCase):
    def test_extract_adds_table_block_and_removes_overlapping_text(self) -> None:
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
                            text="1 Overview",
                            bbox=(0, 0, 100, 20),
                            section_path=["1 Overview"],
                            page_no=1,
                        ),
                        Block(
                            block_id="b2",
                            type="paragraph",
                            text="old table text",
                            bbox=(10, 50, 200, 180),
                            section_path=["1 Overview"],
                            page_no=1,
                        ),
                        Block(
                            block_id="b3",
                            type="paragraph",
                            text="keep me",
                            bbox=(10, 220, 200, 260),
                            section_path=["1 Overview"],
                            page_no=1,
                        ),
                    ],
                )
            ],
        )

        extractor = TableExtractor(
            fitz_module=FakeFitz(
                [
                    FakePdfPage(
                        [
                            FakeTable(
                                bbox=(0, 40, 210, 200),
                                rows=[
                                    ["Table 1 Sales", "", ""],
                                    ["Vendor", "Sales", "Share"],
                                    ["A", "100", "20%"],
                                ],
                            )
                        ]
                    )
                ]
            )
        )

        enriched = extractor.extract(document)
        page_blocks = enriched.pages[0].blocks

        self.assertEqual(len(page_blocks), 3)
        self.assertEqual(page_blocks[1].type, "table")
        self.assertIn("Table 1 Sales", page_blocks[1].text)
        self.assertIn("Vendor | Sales | Share", page_blocks[1].text)
        self.assertEqual(page_blocks[1].section_path, ["1 Overview"])
        self.assertEqual(page_blocks[1].table_json["title"], "Table 1 Sales")
        self.assertEqual(page_blocks[1].table_json["column_count"], 3)
        self.assertEqual(page_blocks[2].text, "keep me")

    def test_extract_skips_single_column_text_box(self) -> None:
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
                            text="line one",
                            bbox=(10, 50, 200, 70),
                            section_path=["Doc"],
                            page_no=1,
                        )
                    ],
                )
            ],
        )

        extractor = TableExtractor(
            fitz_module=FakeFitz(
                [
                    FakePdfPage(
                        [
                            FakeTable(
                                bbox=(0, 40, 210, 200),
                                rows=[
                                    ["This is not a real table"],
                                    ["It is a multi-line callout box"],
                                    ["with one column per row"],
                                    ["that should stay as text"],
                                    ["instead of becoming a table"],
                                ],
                            )
                        ]
                    )
                ]
            )
        )

        enriched = extractor.extract(document)
        self.assertEqual(len(enriched.pages[0].blocks), 1)
        self.assertEqual(enriched.pages[0].blocks[0].type, "paragraph")

    def test_extract_skips_footer_page_number_table(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[Page(page_no=1, blocks=[])],
        )

        extractor = TableExtractor(
            fitz_module=FakeFitz(
                [
                    FakePdfPage(
                        [
                            FakeTable(
                                bbox=(520, 760, 545, 790),
                                rows=[["1"]],
                            )
                        ]
                    )
                ]
            )
        )

        enriched = extractor.extract(document)
        self.assertEqual(enriched.pages[0].blocks, [])

    def test_extract_skips_sparse_contact_box(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[Page(page_no=1, blocks=[])],
        )

        extractor = TableExtractor(
            fitz_module=FakeFitz(
                [
                    FakePdfPage(
                        [
                            FakeTable(
                                bbox=(40, 200, 230, 270),
                                rows=[
                                    ["Analyst: Jane Doe", "S1050525070002"],
                                    ["jane@example.com", ""],
                                    ["Contact: John Roe", "S1050125060011"],
                                    ["john@example.com", ""],
                                ],
                            )
                        ]
                    )
                ]
            )
        )

        enriched = extractor.extract(document)
        self.assertEqual(enriched.pages[0].blocks, [])


if __name__ == "__main__":
    unittest.main()
