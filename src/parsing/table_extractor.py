"""Table extraction helpers."""

from __future__ import annotations

from html import escape
from typing import Any

from src.domain.models.document import Block, Document


class TableExtractor:
    def __init__(self, fitz_module: Any | None = None) -> None:
        self._fitz = fitz_module or self._load_fitz()

    def extract(self, document: Document) -> Document:
        if self._fitz is None or not document.source_file:
            return document

        pdf = self._fitz.open(document.source_file)
        try:
            for page in document.pages:
                pdf_page = pdf[page.page_no - 1]
                page.blocks = self._extract_page_tables(page.blocks, pdf_page, page.page_no)
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

    def _extract_page_tables(
        self,
        blocks: list[Block],
        pdf_page: Any,
        page_no: int,
    ) -> list[Block]:
        table_finder = pdf_page.find_tables()
        if not getattr(table_finder, "tables", None):
            return blocks

        updated_blocks = list(blocks)
        for index, table in enumerate(table_finder.tables, start=1):
            bbox = tuple(float(value) for value in table.bbox)
            normalized_rows = self._normalize_rows(table.extract())
            if not normalized_rows or self._looks_like_text_box(normalized_rows):
                continue

            table_title, content_rows = self._split_title_row(normalized_rows)
            table_block = Block(
                block_id=f"tbl_{page_no}_{index}",
                type="table",
                text=self._rows_to_text(content_rows, table_title),
                bbox=bbox,
                section_path=self._find_section_path(updated_blocks, bbox),
                page_no=page_no,
                table_json={
                    "title": table_title,
                    "rows": content_rows,
                    "row_count": len(content_rows),
                    "column_count": max((len(row) for row in content_rows), default=0),
                },
                table_html=self._rows_to_html(content_rows, table_title),
                source_span={"page_no": page_no, "table_index": index},
            )
            updated_blocks = self._remove_overlapping_blocks(updated_blocks, bbox)
            updated_blocks.append(table_block)

        return self._sort_blocks(updated_blocks)

    def _find_section_path(
        self,
        blocks: list[Block],
        table_bbox: tuple[float, float, float, float],
    ) -> list[str]:
        table_top = table_bbox[1]
        preceding = [
            block
            for block in blocks
            if block.section_path and block.bbox and block.bbox[1] <= table_top
        ]
        if preceding:
            return preceding[-1].section_path.copy()
        return ["Document"]

    def _remove_overlapping_blocks(
        self,
        blocks: list[Block],
        table_bbox: tuple[float, float, float, float],
    ) -> list[Block]:
        remaining: list[Block] = []
        for block in blocks:
            if block.type == "table" or not block.bbox:
                remaining.append(block)
                continue
            if self._intersection_over_block_ratio(block.bbox, table_bbox) >= 0.6:
                continue
            remaining.append(block)
        return remaining

    @staticmethod
    def _intersection_over_block_ratio(
        block_bbox: tuple[float, float, float, float],
        table_bbox: tuple[float, float, float, float],
    ) -> float:
        x0 = max(block_bbox[0], table_bbox[0])
        y0 = max(block_bbox[1], table_bbox[1])
        x1 = min(block_bbox[2], table_bbox[2])
        y1 = min(block_bbox[3], table_bbox[3])
        if x1 <= x0 or y1 <= y0:
            return 0.0
        intersection = (x1 - x0) * (y1 - y0)
        block_area = max(
            (block_bbox[2] - block_bbox[0]) * (block_bbox[3] - block_bbox[1]),
            1e-6,
        )
        return intersection / block_area

    @staticmethod
    def _normalize_rows(rows: list[list[Any]]) -> list[list[str]]:
        normalized: list[list[str]] = []
        for row in rows:
            cleaned_row = [TableExtractor._normalize_cell(cell) for cell in row]
            if any(cell for cell in cleaned_row):
                normalized.append(cleaned_row)
        if not normalized:
            return normalized

        kept_column_indices = [
            index
            for index in range(max(len(row) for row in normalized))
            if any(index < len(row) and row[index] for row in normalized)
        ]
        compact_rows: list[list[str]] = []
        for row in normalized:
            compact_rows.append(
                [row[index] if index < len(row) else "" for index in kept_column_indices]
            )
        return compact_rows

    @staticmethod
    def _split_title_row(rows: list[list[str]]) -> tuple[str | None, list[list[str]]]:
        if not rows:
            return None, rows
        first_row = rows[0]
        non_empty_cells = [cell for cell in first_row if cell]
        if len(non_empty_cells) == 1 and non_empty_cells[0].startswith(("表", "Table")):
            return non_empty_cells[0], rows[1:]
        return None, rows

    @staticmethod
    def _normalize_cell(cell: Any) -> str:
        if cell is None:
            return ""
        return " ".join(str(cell).split())

    @staticmethod
    def _rows_to_text(rows: list[list[str]], table_title: str | None = None) -> str:
        lines: list[str] = []
        if table_title:
            lines.append(f"表格标题: {table_title}")
        header_rows = TableExtractor._infer_header_row_count(rows)
        for index, row in enumerate(rows):
            non_empty_cells = [cell for cell in row if cell]
            if not non_empty_cells:
                continue
            prefix = "表头" if index < header_rows else "数据"
            lines.append(f"{prefix}: {' | '.join(non_empty_cells)}")
        return "\n".join(lines)

    @staticmethod
    def _infer_header_row_count(rows: list[list[str]]) -> int:
        header_rows = 0
        for row in rows[:3]:
            non_empty_cells = [cell for cell in row if cell]
            if not non_empty_cells:
                continue
            if TableExtractor._looks_like_data_row(non_empty_cells):
                break
            header_rows += 1
        return max(header_rows, 1 if rows else 0)

    @staticmethod
    def _looks_like_data_row(non_empty_cells: list[str]) -> bool:
        numeric_like = sum(
            1 for cell in non_empty_cells if any(char.isdigit() for char in cell)
        )
        if numeric_like >= max(1, len(non_empty_cells) // 2):
            return True
        return numeric_like >= 1 and len(non_empty_cells) >= 3

    @staticmethod
    def _looks_like_text_box(rows: list[list[str]]) -> bool:
        non_empty_rows = [[cell for cell in row if cell] for row in rows]
        if not non_empty_rows or any(len(row) > 1 for row in non_empty_rows):
            return False
        if len(non_empty_rows) < 5:
            return False
        average_length = sum(len(row[0]) for row in non_empty_rows) / len(non_empty_rows)
        return average_length >= 12

    @staticmethod
    def _rows_to_html(rows: list[list[str]], table_title: str | None = None) -> str:
        html_rows = []
        if table_title:
            html_rows.append(f"<caption>{escape(table_title)}</caption>")
        for row in rows:
            cells = "".join(f"<td>{escape(cell)}</td>" for cell in row)
            html_rows.append(f"<tr>{cells}</tr>")
        return "<table>" + "".join(html_rows) + "</table>"

    @staticmethod
    def _sort_blocks(blocks: list[Block]) -> list[Block]:
        return sorted(
            blocks,
            key=lambda block: (
                block.bbox[1] if block.bbox else 10**9,
                block.bbox[0] if block.bbox else 10**9,
            ),
        )
