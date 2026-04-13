"""CLI helpers for local retrieval testing."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config.settings import get_settings
from src.retrieval.search_service import SearchService


def build_argument_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run local retrieval against chunk artifacts.")
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=settings.chunks_dir,
        help="Directory containing chunk artifact JSON files.",
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Search query text.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of retrieval results to return.",
    )
    parser.add_argument(
        "--tables-only",
        action="store_true",
        help="Restrict retrieval to table chunks only.",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=220,
        help="How many characters of each chunk to print.",
    )
    return parser


def run_cli(
    query: str,
    chunks_dir: Path,
    top_k: int = 5,
    tables_only: bool = False,
    preview_chars: int = 220,
) -> str:
    service = SearchService.from_chunk_artifacts(chunks_dir)
    results = (
        service.search_tables(query, top_k=top_k)
        if tables_only
        else service.search_chunks(query, top_k=top_k)
    )
    return format_results(
        query=query,
        results=results,
        preview_chars=preview_chars,
        tables_only=tables_only,
    )


def format_results(
    query: str,
    results: list[dict],
    preview_chars: int = 220,
    tables_only: bool = False,
) -> str:
    mode = "tables" if tables_only else "chunks"
    lines = [f'Query: "{query}"', f"Mode: {mode}", f"Hits: {len(results)}"]
    if not results:
        lines.append("No results found.")
        return "\n".join(lines)

    for rank, item in enumerate(results, start=1):
        chunk = item["chunk"]
        preview = chunk.text.replace("\n", " ").strip()
        if len(preview) > preview_chars:
            preview = preview[:preview_chars].rstrip() + "..."
        score = item.get("score", 0.0)
        sources = ",".join(item.get("sources", [item.get("source", "unknown")]))
        section = " > ".join(chunk.section_path) if chunk.section_path else "Document"
        lines.extend(
            [
                f"{rank}. {chunk.chunk_id}",
                f"   type={chunk.chunk_type} page={chunk.page_no} score={score:.4f} sources={sources}",
                f"   section={section}",
                f"   text={preview}",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    args = build_argument_parser().parse_args()
    output = run_cli(
        query=args.query,
        chunks_dir=args.chunks_dir,
        top_k=args.top_k,
        tables_only=args.tables_only,
        preview_chars=args.preview_chars,
    )
    print(output)


if __name__ == "__main__":
    main()
