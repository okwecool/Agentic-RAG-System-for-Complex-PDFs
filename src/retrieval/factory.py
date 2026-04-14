"""Factories for retrieval components."""

from __future__ import annotations

from src.config.settings import Settings
from src.domain.protocols.reranker import RerankerProvider
from src.retrieval.hybrid_fusion import HybridFusion
from src.retrieval.rerankers.noop import NoOpReranker
from src.retrieval.rerankers.transformers_cross_encoder import (
    TransformersCrossEncoderReranker,
)


def create_hybrid_fusion(settings: Settings) -> HybridFusion:
    return HybridFusion(
        mode=settings.fusion_mode,
        rrf_k=settings.fusion_rrf_k,
        bm25_weight=settings.fusion_bm25_weight,
        vector_weight=settings.fusion_vector_weight,
    )


def create_reranker(settings: Settings) -> RerankerProvider:
    provider_name = settings.reranker_provider.lower().strip()
    if provider_name == "noop":
        return NoOpReranker()
    if provider_name == "local_transformers":
        if not settings.local_reranker_model_dir:
            raise ValueError("Missing local reranker model directory.")
        return TransformersCrossEncoderReranker(
            model_name_or_path=str(settings.local_reranker_model_dir),
            top_n=settings.reranker_top_n,
            batch_size=settings.reranker_batch_size,
        )
    raise ValueError(f"Unsupported reranker provider: {settings.reranker_provider}")
