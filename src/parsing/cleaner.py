"""Block cleaning helpers."""

from collections import Counter
import re

from src.domain.models.document import Block, Document, Page


DISCLAIMER_FOOTER_PATTERNS = (
    re.compile(r"\bdisclosures?\b", re.IGNORECASE),
    re.compile(r"\bdisclaimer\b", re.IGNORECASE),
    re.compile(r"\blegal statement\b", re.IGNORECASE),
    re.compile(r"\bimportant notice\b", re.IGNORECASE),
    re.compile(r"信息披露"),
    re.compile(r"法律声明"),
    re.compile(r"免责声明"),
    re.compile(r"重要声明"),
)

STRUCTURED_HEADING_PATTERN = re.compile(
    r"^("
    r"\d{1,2}(?:\.\d+){0,3}"
    r"|[IVXLC]+[.)]?"
    r"|[一二三四五六七八九十]+[、.]?"
    r")\s*.+"
)


class DocumentCleaner:
    def clean(self, document: Document) -> Document:
        repeated_noise = self._find_repeated_noise(document)
        repeated_positional_noise = self._find_repeated_positional_noise(document)

        for page in document.pages:
            cleaned_blocks: list[Block] = []
            for block in page.blocks:
                cleaned_text = self._normalize_text(block.text)
                if not cleaned_text:
                    continue
                block.text = cleaned_text
                if self._is_noise(
                    block=block,
                    page=page,
                    repeated_noise=repeated_noise,
                    repeated_positional_noise=repeated_positional_noise,
                ):
                    continue
                cleaned_blocks.append(block)
            page.blocks = self._merge_wrapped_blocks(cleaned_blocks)
        return document

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _is_noise(
        self,
        block: Block,
        page: Page,
        repeated_noise: set[str],
        repeated_positional_noise: set[tuple[str, str]],
    ) -> bool:
        compact = block.text.strip()
        if len(compact) <= 1:
            return True
        if re.fullmatch(r"\d+", compact):
            return True
        if re.fullmatch(r"page\s+\d+(\s+of\s+\d+)?", compact.lower()):
            return True
        if compact in repeated_noise:
            return True

        zone = self._position_zone(block, page)
        if zone and (compact, zone) in repeated_positional_noise:
            return True

        return self._is_visual_noise(block, page)

    @staticmethod
    def _find_repeated_noise(document: Document) -> set[str]:
        if len(document.pages) < 2:
            return set()
        counts: Counter[str] = Counter()
        for page in document.pages:
            unique_texts = {
                re.sub(r"\s+", " ", block.text).strip()
                for block in page.blocks
                if block.text and len(block.text.strip()) <= 30
            }
            counts.update(unique_texts)
        return {text for text, count in counts.items() if count >= 2}

    def _find_repeated_positional_noise(self, document: Document) -> set[tuple[str, str]]:
        counts: Counter[tuple[str, str]] = Counter()
        for page in document.pages:
            for block in page.blocks:
                if not block.text or not block.bbox:
                    continue
                text = re.sub(r"\s+", " ", block.text).strip()
                if len(text) > 80:
                    continue
                zone = self._position_zone(block, page)
                if zone:
                    counts[(text, zone)] += 1
        return {item for item, count in counts.items() if count >= 2}

    @staticmethod
    def _position_zone(block: Block, page: Page) -> str | None:
        if not block.bbox or not page.height:
            return None
        top_ratio = block.bbox[1] / max(page.height, 1.0)
        bottom_ratio = block.bbox[3] / max(page.height, 1.0)
        if top_ratio <= 0.12:
            return "header"
        if bottom_ratio >= 0.88:
            return "footer"
        return None

    def _is_visual_noise(self, block: Block, page: Page) -> bool:
        if not block.bbox:
            return False
        text = block.text.strip()
        width = block.bbox[2] - block.bbox[0]
        height = block.bbox[3] - block.bbox[1]
        page_width = page.width or 1.0

        if self._looks_like_chart_axis_label(text, width, page_width):
            return True
        if self._looks_like_chart_legend(block, page):
            return True
        if self._looks_like_vertical_cover_label(text, width, height):
            return True
        if self._looks_like_decorative_strip(block, page):
            return True
        if self._looks_like_disclaimer_footer(text, block, page):
            return True
        return False

    @staticmethod
    def _looks_like_chart_axis_label(text: str, width: float, page_width: float) -> bool:
        compact = text.replace("\n", " ").strip()
        if len(compact) > 18:
            return False
        if width > page_width * 0.28:
            return False
        if re.fullmatch(r"[-+]?\d+(\.\d+)?%?", compact):
            return True
        if re.fullmatch(r"\d{4}[-/]\d{1,2}", compact):
            return True
        return bool(re.fullmatch(r"[\d.\-+% ]+", compact))

    @staticmethod
    def _looks_like_vertical_cover_label(text: str, width: float, height: float) -> bool:
        compact = text.replace("\n", "").strip()
        if len(compact) < 4:
            return False
        if width > 25 and height < 60:
            return False
        return "\n" in text and height > width * 3

    @staticmethod
    def _looks_like_chart_legend(block: Block, page: Page) -> bool:
        if not block.bbox or not page.width:
            return False
        text = block.text.strip()
        width = block.bbox[2] - block.bbox[0]
        left_ratio = block.bbox[0] / page.width
        if left_ratio > 0.35:
            return False
        if width > page.width * 0.25:
            return False
        if len(text.replace("\n", "")) > 24:
            return False
        return "\n" in text and block.type == "paragraph"

    @staticmethod
    def _looks_like_decorative_strip(block: Block, page: Page) -> bool:
        if block.type != "table" or not block.bbox or not page.width or not page.height:
            return False
        width = block.bbox[2] - block.bbox[0]
        height = block.bbox[3] - block.bbox[1]
        if width > page.width * 0.08:
            return False
        return height >= page.height * 0.25

    @staticmethod
    def _looks_like_disclaimer_footer(text: str, block: Block, page: Page) -> bool:
        if not block.bbox or not page.height:
            return False
        if block.bbox[1] / page.height < 0.82:
            return False
        compact = text.replace("\n", " ").strip()
        if re.search(r"\b\d+\s*/\s*\d+\b", compact):
            return True
        return any(pattern.search(compact) for pattern in DISCLAIMER_FOOTER_PATTERNS)

    def _merge_wrapped_blocks(self, blocks: list[Block]) -> list[Block]:
        if not blocks:
            return []

        merged: list[Block] = []
        current = blocks[0]
        for nxt in blocks[1:]:
            if self._should_merge(current, nxt):
                current = self._merge_block_pair(current, nxt)
            else:
                merged.append(self._demote_suspicious_heading(current))
                current = nxt
        merged.append(self._demote_suspicious_heading(current))
        return merged

    def _should_merge(self, current: Block, nxt: Block) -> bool:
        if current.type == "table" or nxt.type == "table":
            return False
        if current.type == "list_item" or nxt.type == "list_item":
            return False
        if not current.bbox or not nxt.bbox:
            return False
        if self._looks_like_structured_heading(current.text):
            return False
        if self._looks_like_structured_heading(nxt.text):
            return False
        if self._ends_with_terminal_punctuation(current.text) and len(current.text) > 24:
            return False
        if len(current.text) > 120:
            return False

        left_delta = abs(current.bbox[0] - nxt.bbox[0])
        right_delta = abs(current.bbox[2] - nxt.bbox[2])
        vertical_gap = nxt.bbox[1] - current.bbox[3]
        if not (left_delta <= 45 and right_delta <= 70 and 0 <= vertical_gap <= 28):
            return False

        current_len = len(current.text.strip())
        next_len = len(nxt.text.strip())
        if current_len <= 40 and next_len <= 40:
            return True
        return not self._ends_with_terminal_punctuation(current.text)

    def _merge_block_pair(self, current: Block, nxt: Block) -> Block:
        merged_bbox = (
            min(current.bbox[0], nxt.bbox[0]),
            min(current.bbox[1], nxt.bbox[1]),
            max(current.bbox[2], nxt.bbox[2]),
            max(current.bbox[3], nxt.bbox[3]),
        ) if current.bbox and nxt.bbox else current.bbox or nxt.bbox
        return Block(
            block_id=f"{current.block_id}+{nxt.block_id}",
            type="paragraph",
            text=f"{current.text}\n\n{nxt.text}",
            bbox=merged_bbox,
            section_path=current.section_path.copy(),
            page_no=current.page_no or nxt.page_no,
            source_span={"merged_block_ids": [current.block_id, nxt.block_id]},
        )

    def _demote_suspicious_heading(self, block: Block) -> Block:
        if block.type != "heading":
            return block
        if self._looks_like_structured_heading(block.text):
            return block
        if len(block.text.strip()) <= 20:
            return block
        return Block(
            block_id=block.block_id,
            type="paragraph",
            text=block.text,
            bbox=block.bbox,
            section_path=block.section_path.copy(),
            page_no=block.page_no,
            table_html=block.table_html,
            table_json=block.table_json,
            source_span=block.source_span,
        )

    @staticmethod
    def _looks_like_structured_heading(text: str) -> bool:
        return bool(STRUCTURED_HEADING_PATTERN.match(text.strip()))

    @staticmethod
    def _ends_with_terminal_punctuation(text: str) -> bool:
        return text.strip().endswith(("。", "！", "？", "；", "：", ".", "!", "?", ";", ":"))
