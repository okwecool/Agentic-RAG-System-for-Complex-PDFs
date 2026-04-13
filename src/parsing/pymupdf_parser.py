"""PyMuPDF-based parser skeleton."""

from pathlib import Path
import re
from typing import Any

from src.domain.models.document import Block, Document, Page
from src.utils.ids import build_block_id


class PyMuPdfParser:
    def __init__(self) -> None:
        self._fitz = self._load_fitz()

    def parse(self, file_path: str) -> Document:
        if self._fitz is None:
            raise RuntimeError(
                "PyMuPDF is not installed. Install the 'pymupdf' package to parse PDFs."
            )

        source = Path(file_path)
        title = source.stem
        document = Document(
            doc_id="pending",
            title=title,
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

            block_index += 1
            block_type = self._infer_block_type(
                text=text,
                line_count=line_count,
                max_size=max_size,
                bold_ratio=(bold_spans / max(1, span_count)),
            )
            bbox = raw_block.get("bbox")
            blocks.append(
                Block(
                    block_id=build_block_id(page_no, block_index),
                    type=block_type,
                    text=text,
                    bbox=tuple(float(value) for value in bbox) if bbox else None,
                    page_no=page_no,
                    source_span={"page_no": page_no, "block_index": block_index},
                )
            )

        return blocks

    @staticmethod
    def _infer_block_type(
        text: str,
        line_count: int,
        max_size: float,
        bold_ratio: float,
    ) -> str:
        stripped = text.strip()
        if re.match(
            r"^((\d{1,2}(?:\.\d+){0,3})|([一二三四五六七八九十]+、)|([IVXLC]+[\.、\)]?))\s+.+",
            stripped,
        ) and line_count <= 3:
            return "heading"
        if stripped.startswith(("-", "*", "•")):
            return "list_item"
        if (
            line_count <= 2
            and len(stripped) <= 40
            and not stripped.endswith(("。", "；", ";", "，", ",", "：", ":"))
            and (max_size >= 14 or bold_ratio >= 0.85)
        ):
            return "heading"
        return "paragraph"
