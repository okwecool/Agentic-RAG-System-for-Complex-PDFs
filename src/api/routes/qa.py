"""Question answering routes."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas.qa import QaRequest, QaResponse
from src.config.settings import get_settings
from src.generation.qa_service import QaService

router = APIRouter(tags=["qa"])


@lru_cache(maxsize=1)
def get_qa_service() -> QaService:
    settings = get_settings()
    return QaService.from_settings(settings)


@router.post("/qa/ask", response_model=QaResponse)
def ask_question(
    payload: QaRequest,
    qa_service: QaService = Depends(get_qa_service),
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
