"""CLI entrypoint for PDF ingestion."""

import argparse
import json
from pathlib import Path

from src.chunking.chunker import SectionAwareChunker
from src.chunking.rules import ChunkingConfig
from src.config.settings import get_settings
from src.ingestion.pipeline import IngestionPipeline
from src.parsing.pymupdf_parser import PyMuPdfParser


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PDF ingestion pipeline.")
    parser.add_argument(
        "--source-dir",
        type=str,
        default=None,
        help="Optional override for the PDF source directory.",
    )
    parser.add_argument(
        "--target-size",
        type=int,
        default=800,
        help="Target character size for each chunk.",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=100,
        help="Character overlap between adjacent chunks.",
    )
    parser.add_argument(
        "--preview-doc",
        type=str,
        default=None,
        help="Preview chunks for one PDF path instead of the whole directory.",
    )
    parser.add_argument(
        "--preview-limit",
        type=int,
        default=5,
        help="How many chunks to print in preview mode.",
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    settings = get_settings()
    if args.source_dir:
        settings.source_pdf_dir = Path(args.source_dir)

    chunker = SectionAwareChunker(
        ChunkingConfig(
            target_size=args.target_size,
            overlap=args.overlap,
        )
    )
    pipeline = IngestionPipeline(
        settings=settings,
        parser=PyMuPdfParser(),
        chunker=chunker,
    )

    if args.preview_doc:
        preview_path = Path(args.preview_doc)
        document = pipeline.parser.parse(str(preview_path))
        document = pipeline.cleaner.clean(document)
        document = pipeline.table_extractor.extract(document)
        document = pipeline.section_builder.apply(document)
        document.chunks = pipeline.chunker.chunk(document)
        payload = {
            "title": document.title,
            "page_count": len(document.pages),
            "chunk_count": len(document.chunks),
            "chunks": [
                {
                    "page_no": chunk.page_no,
                    "chunk_type": chunk.chunk_type,
                    "section_path": chunk.section_path,
                    "char_count": len(chunk.text),
                    "text": chunk.text[:400],
                }
                for chunk in document.chunks[: args.preview_limit]
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    result = pipeline.run()
    print(
        json.dumps(
            {
                "scanned_files": result.scanned_files,
                "successful_documents": result.successful_documents,
                "failed_documents": result.failed_documents,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
