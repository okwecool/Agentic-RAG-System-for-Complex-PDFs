"""Command-line question answering entrypoint."""

from __future__ import annotations

import argparse
import logging
import sys

from src.config.settings import get_settings
from src.generation.qa_service import QaService


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def format_answer(result: dict) -> str:
    lines = [
        f'Query: "{result["query"]}"',
        f'Confidence: {result["confidence"]}',
        f'Model: {result.get("model") or "unknown"}',
        f'Embedding: {result["embedding_backend"]}',
        "",
        "Answer:",
        result["answer"],
    ]
    citations = result.get("citations", [])
    if citations:
        lines.append("")
        lines.append("Citations:")
        for idx, citation in enumerate(citations, start=1):
            lines.append(
                f'{idx}. {citation["doc_id"]} page={citation["page_no"]} chunk={citation["chunk_id"]}'
            )
            excerpt = (citation.get("excerpt") or "").strip()
            if excerpt:
                lines.append(f"   {excerpt}")
    evidence = result.get("evidence", [])
    if evidence:
        lines.append("")
        lines.append("Evidence Preview:")
        for idx, item in enumerate(evidence, start=1):
            preview = item["text"].strip().replace("\n", " ")
            lines.append(
                f'{idx}. {item["chunk_id"]} type={item["chunk_type"]} '
                f'page={item["page_no"]} score={item["score"]:.4f}'
            )
            lines.append(f"   {preview[:180]}")
    return "\n".join(lines)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    configure_logging()
    parser = argparse.ArgumentParser(description="Ask questions over indexed PDF evidence.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--tables-only", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    service = QaService.from_settings(settings)
    result = service.answer(
        query=args.query,
        top_k=args.top_k,
        tables_only=args.tables_only,
    )
    print(format_answer(result))


if __name__ == "__main__":
    main()
