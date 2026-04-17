import unittest

from src.domain.models.document import Block, Document, Page
from src.parsing.cleaner import DocumentCleaner
from src.parsing.pymupdf_parser import PyMuPdfParser
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
        self.assertEqual(cleaned.pages[0].blocks[0].text, "Hello world next line")

    def test_cleaner_joins_wrapped_paragraph_lines(self) -> None:
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
                            text="Sora 2 在物理模拟精度上实现了对初代 Sora 的突破性升级。\n针对初代“水流方向不自然”的问题，\nSora 2 升级了流体模拟精度。",
                            page_no=1,
                        )
                    ],
                )
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertNotIn("\n", cleaned.pages[0].blocks[0].text)
        self.assertIn("针对初代", cleaned.pages[0].blocks[0].text)

    def test_cleaner_normalizes_private_use_bullet(self) -> None:
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
                            text="\uf06e\nOpenAI Sora 2 相较于初代实现了升级。",
                            page_no=1,
                        )
                    ],
                )
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertTrue(cleaned.pages[0].blocks[0].text.startswith("• OpenAI"))

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

    def test_cleaner_merges_wrapped_blocks_without_artificial_paragraph_breaks(self) -> None:
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
                            text="针对初代“水流方向不自",
                            bbox=(80, 100, 500, 114),
                            page_no=1,
                        ),
                        Block(
                            block_id="b2",
                            type="paragraph",
                            text="然”的问题，Sora 2 升级了流体模拟精度。",
                            bbox=(80, 118, 500, 132),
                            page_no=1,
                        ),
                    ],
                )
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertEqual(len(cleaned.pages[0].blocks), 1)
        self.assertNotIn("\n", cleaned.pages[0].blocks[0].text)
        self.assertIn("不自然", cleaned.pages[0].blocks[0].text)

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

    def test_cleaner_removes_chart_axis_noise_and_footer(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[
                Page(
                    page_no=1,
                    width=600,
                    height=800,
                    blocks=[
                        Block(
                            block_id="b1",
                            type="paragraph",
                            text="36%",
                            bbox=(10, 200, 30, 215),
                            page_no=1,
                        ),
                        Block(
                            block_id="b2",
                            type="paragraph",
                            text="2025-02",
                            bbox=(20, 260, 90, 275),
                            page_no=1,
                        ),
                        Block(
                            block_id="b3",
                            type="paragraph",
                            text="Please refer to disclosures 1 / 3",
                            bbox=(20, 760, 300, 790),
                            page_no=1,
                        ),
                        Block(
                            block_id="b4",
                            type="paragraph",
                            text="Main body paragraph",
                            bbox=(150, 300, 500, 330),
                            page_no=1,
                        ),
                    ],
                )
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertEqual(len(cleaned.pages[0].blocks), 1)
        self.assertEqual(cleaned.pages[0].blocks[0].text, "Main body paragraph")

    def test_cleaner_keeps_mid_page_body_with_legal_terms(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[
                Page(
                    page_no=1,
                    width=600,
                    height=800,
                    blocks=[
                        Block(
                            block_id="b1",
                            type="paragraph",
                            text="This section discusses the legal statement requirements for vendors.",
                            bbox=(80, 320, 520, 350),
                            page_no=1,
                        )
                    ],
                )
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertEqual(len(cleaned.pages[0].blocks), 1)
        self.assertIn("legal statement requirements", cleaned.pages[0].blocks[0].text)

    def test_cleaner_removes_generic_source_note_blocks(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[
                Page(
                    page_no=1,
                    width=600,
                    height=800,
                    blocks=[
                        Block(
                            block_id="b1",
                            type="heading",
                            text="46\n数据来源：公司公告、研究所",
                            bbox=(60, 80, 260, 120),
                            page_no=1,
                        ),
                        Block(
                            block_id="b2",
                            type="paragraph",
                            text="Main body paragraph",
                            bbox=(80, 200, 500, 260),
                            page_no=1,
                        ),
                    ],
                )
            ],
        )

        cleaned = DocumentCleaner().clean(document)

        self.assertEqual(len(cleaned.pages[0].blocks), 1)
        self.assertEqual(cleaned.pages[0].blocks[0].text, "Main body paragraph")

    def test_cleaner_demotes_short_headings_on_label_dense_pages(self) -> None:
        blocks = [
            Block(
                block_id=f"b{i}",
                type="heading",
                text=text,
                bbox=(80, 60 + i * 20, 260, 76 + i * 20),
                page_no=1,
            )
            for i, text in enumerate(
                [
                    "封闭模式",
                    "开放模式",
                    "IBM 联盟",
                    "标准化",
                    "价格敏感",
                    "体验敏感",
                ],
                start=1,
            )
        ]
        blocks.extend(
            [
                Block(
                    block_id="b100",
                    type="paragraph",
                    text="这是一段相对完整的正文说明，用来保证页面上仍然存在叙述性内容。",
                    bbox=(300, 120, 560, 200),
                    page_no=1,
                ),
                Block(
                    block_id="b101",
                    type="paragraph",
                    text="另一段说明文字，用于模拟图表页上的正文解释。",
                    bbox=(300, 220, 560, 280),
                    page_no=1,
                ),
            ]
        )
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[Page(page_no=1, width=600, height=800, blocks=blocks)],
        )

        cleaned = DocumentCleaner().clean(document)

        heading_count = sum(1 for block in cleaned.pages[0].blocks if block.type == "heading")
        paragraph_count = sum(1 for block in cleaned.pages[0].blocks if block.type == "paragraph")
        self.assertLessEqual(heading_count, 1)
        self.assertGreaterEqual(paragraph_count, 3)

    def test_section_builder_ignores_date_and_source_headings(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[
                Page(
                    page_no=1,
                    blocks=[
                        Block(block_id="b1", type="heading", text="2025 年 12 月 13 日"),
                        Block(block_id="b2", type="paragraph", text="封面正文"),
                        Block(block_id="b3", type="heading", text="98 数据来源：公司公告、研究所"),
                        Block(block_id="b4", type="paragraph", text="后续正文"),
                        Block(block_id="b5", type="heading", text="1 正文开始"),
                        Block(block_id="b6", type="paragraph", text="章节正文"),
                    ],
                )
            ],
        )

        enriched = SectionBuilder().apply(document)

        self.assertEqual(enriched.pages[0].blocks[1].section_path, ["Document"])
        self.assertEqual(enriched.pages[0].blocks[3].section_path, ["Document"])
        self.assertEqual(enriched.pages[0].blocks[5].section_path, ["1 正文开始"])


    def test_parser_does_not_treat_numeric_label_as_heading(self) -> None:
        block_type = PyMuPdfParser._infer_block_type(
            text="70% 。",
            line_count=1,
            max_size=15.0,
            bold_ratio=1.0,
        )

        self.assertEqual(block_type, "paragraph")


if __name__ == "__main__":
    unittest.main()
