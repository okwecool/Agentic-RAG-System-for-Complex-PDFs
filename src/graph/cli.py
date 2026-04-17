"""CLI for the agentic workflow path."""

from __future__ import annotations

import argparse
import logging
import sys

from src.config.settings import get_settings
from src.generation.agentic_qa_service import AgenticQaService
from src.generation.cli import format_answer


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    configure_logging()
    parser = argparse.ArgumentParser(description="Ask questions via the agentic workflow.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--tables-only", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    service = AgenticQaService.from_settings(settings)
    result = service.answer(
        query=args.query,
        top_k=args.top_k,
        tables_only=args.tables_only,
    )
    print(format_answer(result))


if __name__ == "__main__":
    main()
