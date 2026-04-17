"""Agentic question answering routes."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas.qa import QaRequest, QaResponse
from src.config.settings import get_settings
from src.generation.agentic_qa_service import AgenticQaService

router = APIRouter(tags=["agentic-qa"])


@lru_cache(maxsize=1)
def get_agentic_qa_service() -> AgenticQaService:
    settings = get_settings()
    return AgenticQaService.from_settings(settings)


@router.post("/qa/ask-agentic", response_model=QaResponse)
def ask_question_agentic(
    payload: QaRequest,
    qa_service: AgenticQaService = Depends(get_agentic_qa_service),
) -> QaResponse:
    try:
        result = qa_service.answer(
            query=payload.query,
            top_k=payload.top_k,
            tables_only=payload.tables_only,
        )
    except (FileNotFoundError, ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return QaResponse.model_validate(result)
