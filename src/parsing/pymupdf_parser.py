"""PyMuPDF-based parser skeleton."""

from pathlib import Path

from src.domain.models.document import Block, Document, Page
from src.utils.ids import build_block_id


class PyMuPdfParser:
    def parse(self, file_path: str) -> Document:
        source = Path(file_path)
        title = source.stem
        document = Document(
            doc_id="pending",
            title=title,
            source_file=file_path,
        )

        # Placeholder page so downstream code can be exercised before the
        # real parser is implemented.
        document.pages.append(
            Page(
                page_no=1,
                blocks=[
                    Block(
                        block_id=build_block_id(1, 1),
                        type="placeholder",
                        text=f"Parser skeleton for {title}",
                        section_path=["Document"],
                    )
                ],
            )
        )
        return document

