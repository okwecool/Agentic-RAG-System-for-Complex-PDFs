"""Block cleaning helpers."""

from collections import Counter
import re

from src.domain.models.document import Block, Document


class DocumentCleaner:
    def clean(self, document: Document) -> Document:
        repeated_noise = self._find_repeated_noise(document)
        for page in document.pages:
            cleaned_blocks: list[Block] = []
            for block in page.blocks:
                cleaned_text = self._normalize_text(block.text)
                if not cleaned_text or self._is_noise(cleaned_text, repeated_noise):
                    continue
                block.text = cleaned_text
                cleaned_blocks.append(block)
            page.blocks = self._merge_wrapped_blocks(cleaned_blocks)
        return document

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _is_noise(text: str, repeated_noise: set[str]) -> bool:
        compact = text.strip()
        if len(compact) <= 1:
            return True
        if re.fullmatch(r"\d+", compact):
            return True
        if re.fullmatch(r"page\s+\d+(\s+of\s+\d+)?", compact.lower()):
            return True
        if compact in repeated_noise:
            return True
        return False

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
        stripped = text.strip()
        return bool(
            re.match(
                r"^(\d{1,2}(?:\.\d+){0,3}|[IVXLC]+[.)]?|[一二三四五六七八九十]+、)\s+.+",
                stripped,
            )
        )

    @staticmethod
    def _ends_with_terminal_punctuation(text: str) -> bool:
        return text.strip().endswith(("。", "！", "？", ".", "!", "?", "；", ";", "：", ":"))
