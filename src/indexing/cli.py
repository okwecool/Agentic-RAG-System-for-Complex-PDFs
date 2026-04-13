"""CLI entrypoint for local retrieval index building."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config.settings import get_settings
from src.indexing.bm25_index import Bm25Index
from src.indexing.embeddings import EmbeddingService
from src.indexing.index_builder import IndexBuilder
from src.indexing.vector_index import VectorIndex


def build_argument_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Build a local retrieval index from chunk artifacts.")
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=settings.chunks_dir,
        help="Directory containing chunk artifact JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.indexes_dir / "retrieval_cache",
        help="Directory used to persist vector index artifacts.",
    )
    parser.add_argument(
        "--embedding-model-path",
        type=Path,
        default=settings.local_embedding_model_dir,
        help="Optional local SentenceTransformer model path.",
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    embedding_service = EmbeddingService(
        model_name_or_path=str(args.embedding_model_path) if args.embedding_model_path else None
    )
    builder = IndexBuilder(
        embedding_service=embedding_service,
        vector_index=VectorIndex(),
        bm25_index=Bm25Index(),
    )
    manifest = builder.build_and_persist(
        chunks_dir=args.chunks_dir,
        output_dir=args.output_dir,
    )
    print(
        "\n".join(
            [
                f"Output: {args.output_dir}",
                f"Embedding: {manifest['embedding_backend']}",
                f"Chunks: {manifest['chunk_count']}",
            ]
        )
    )


if __name__ == "__main__":
    main()
