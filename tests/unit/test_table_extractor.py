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
    def __init__(self, tables) -> None:
        self._tables = tables

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
                                    ["表1 销量", "", ""],
                                    ["厂商", "销量", "份额"],
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
        self.assertIn("厂商 | 销量 | 份额", page_blocks[1].text)
        self.assertEqual(page_blocks[1].section_path, ["1 Overview"])
        self.assertEqual(page_blocks[2].text, "keep me")


if __name__ == "__main__":
    unittest.main()
