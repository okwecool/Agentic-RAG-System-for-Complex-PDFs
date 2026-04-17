"""PyMuPDF-based parser."""

from pathlib import Path
import re
from typing import Any

from src.domain.models.document import Block, Document, Page
from src.utils.ids import build_block_id


STRUCTURED_HEADING_PATTERN = re.compile(
    r"^("
    r"\d{1,2}(?:\.\d+){0,3}(?:[.)．、]|\s+)"
    r"|[IVXLC]+(?:[.)]|\s+)"
    r"|[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343]+(?:[、.)．]|\s+)"
    r")\s*.+"
)

DATE_OR_PERIOD_PATTERN = re.compile(
    r"(20\d{2}(?:[-/\u5e74]\d{1,2}(?:[-/\u6708]\d{1,2}\u65e5?)?)?|"
    r"\d{4}[qehm]\d{1,2}|"
    r"\d{4}[\u5e74]?\d{0,2}[\u6708]?\d{0,2}[\u65e5]?)"
)


class PyMuPdfParser:
    def __init__(self) -> None:
        self._fitz = self._load_fitz()

    def parse(self, file_path: str) -> Document:
        if self._fitz is None:
            raise RuntimeError(
                "PyMuPDF is not installed. Install the 'pymupdf' package to parse PDFs."
            )

        source = Path(file_path)
        document = Document(
            doc_id="pending",
            title=source.stem,
            source_file=file_path,
        )

        pdf = self._fitz.open(file_path)
        try:
            for page_index, pdf_page in enumerate(pdf, start=1):
                page_dict = pdf_page.get_text("dict")
                document.pages.append(
                    Page(
                        page_no=page_index,
                        width=float(page_dict.get("width", pdf_page.rect.width)),
                        height=float(page_dict.get("height", pdf_page.rect.height)),
                        blocks=self._parse_page_blocks(page_index, page_dict),
                    )
                )
        finally:
            pdf.close()
        return document

    @staticmethod
    def _load_fitz() -> Any | None:
        try:
            import fitz
        except ModuleNotFoundError:
            return None
        return fitz

    def _parse_page_blocks(self, page_no: int, page_dict: dict[str, Any]) -> list[Block]:
        blocks: list[Block] = []
        block_index = 0

        for raw_block in page_dict.get("blocks", []):
            if raw_block.get("type") != 0:
                continue

            text_lines: list[str] = []
            max_size = 0.0
            bold_spans = 0
            span_count = 0
            line_count = 0

            for line in raw_block.get("lines", []):
                line_count += 1
                line_parts: list[str] = []
                for span in line.get("spans", []):
                    span_text = str(span.get("text", "")).strip()
                    if not span_text:
                        continue
                    line_parts.append(span_text)
                    max_size = max(max_size, float(span.get("size", 0.0)))
                    span_count += 1
                    if int(span.get("flags", 0)) & 16:
                        bold_spans += 1
                if line_parts:
                    text_lines.append(" ".join(line_parts))

            text = "\n".join(text_lines).strip()
            if not text:
                continue

            bold_ratio = bold_spans / max(1, span_count)
            block_index += 1
            bbox = raw_block.get("bbox")
            blocks.append(
                Block(
                    block_id=build_block_id(page_no, block_index),
                    type=self._infer_block_type(
                        text=text,
                        line_count=line_count,
                        max_size=max_size,
                        bold_ratio=bold_ratio,
                    ),
                    text=text,
                    bbox=tuple(float(value) for value in bbox) if bbox else None,
                    page_no=page_no,
                    content_role=self._infer_content_role(text=text, block_type=self._infer_block_type(
                        text=text,
                        line_count=line_count,
                        max_size=max_size,
                        bold_ratio=bold_ratio,
                    )),
                    source_span={
                        "page_no": page_no,
                        "block_index": block_index,
                        "line_count": line_count,
                        "max_size": max_size,
                        "bold_ratio": round(bold_ratio, 4),
                    },
                )
            )
        return blocks

    @staticmethod
    def _infer_content_role(text: str, block_type: str) -> str:
        stripped = text.strip()
        lowered = stripped.lower()
        if block_type == "list_item":
            return "list_item"
        if block_type == "heading":
            if lowered.startswith(("图表", "图", "figure")):
                return "figure_caption"
            if lowered.startswith(("表", "table")):
                return "table_caption"
            return "heading"
        if block_type == "table":
            return "table"
        return "narrative_paragraph"

    @staticmethod
    def _infer_block_type(
        text: str,
        line_count: int,
        max_size: float,
        bold_ratio: float,
    ) -> str:
        stripped = text.strip()
        if PyMuPdfParser._looks_like_structured_heading(stripped) and line_count <= 3:
            return "heading"
        if stripped.startswith(("-", "*", "•", "◼", "◆", "➢")):
            return "list_item"
        if (
            line_count <= 2
            and 4 <= len(stripped) <= 36
            and not stripped.endswith(("。", "！", "？", "；", "：", ".", "!", "?", ";", ":"))
            and max_size >= 14
            and bold_ratio >= 0.6
            and not PyMuPdfParser._looks_like_date_or_period_label(stripped)
            and not PyMuPdfParser._looks_like_page_or_source_note(stripped)
            and not PyMuPdfParser._looks_mostly_numeric(stripped)
        ):
            return "heading"
        return "paragraph"

    @staticmethod
    def _looks_like_structured_heading(text: str) -> bool:
        return bool(STRUCTURED_HEADING_PATTERN.match(text))

    @staticmethod
    def _looks_like_date_or_period_label(text: str) -> bool:
        normalized = re.sub(r"\s+", "", text.lower())
        return bool(DATE_OR_PERIOD_PATTERN.fullmatch(normalized))

    @staticmethod
    def _looks_like_page_or_source_note(text: str) -> bool:
        compact = re.sub(r"\s+", " ", text.strip()).lower()
        if (
            "\u6570\u636e\u6765\u6e90" in compact
            or "\u8d44\u6599\u6765\u6e90" in compact
            or "source:" in compact
        ):
            return True
        return bool(re.fullmatch(r"\d{1,4}", compact))

    @staticmethod
    def _looks_mostly_numeric(text: str) -> bool:
        meaningful = [char for char in text if not char.isspace()]
        if not meaningful:
            return False
        numeric_like = sum(
            1
            for char in meaningful
            if char.isdigit() or char in {"%", ".", "-", "/", "+", "E", ","}
        )
        return numeric_like / len(meaningful) >= 0.45
