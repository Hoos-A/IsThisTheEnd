"""Endpoints orchestrating LLM extraction and billing suggestions."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..retrieval import ranker
from ..rules import engine
from ..schemas import (
    CodeCandidate,
    LLMExtractRequest,
    LLMExtractResponse,
    LLMSuggestRequest,
    LLMSuggestResponse,
    ValidationRequest,
    ValidationResult,
)
from ..services.llm import provider

router = APIRouter(prefix="", tags=["llm"])


@router.post("/llm/extract", response_model=LLMExtractResponse)
async def extract_payload(payload: LLMExtractRequest) -> LLMExtractResponse:
    return await provider.extract(payload.transcript)


async def _suggest_from_transcript(transcript: str) -> LLMSuggestResponse:
    extraction = await provider.extract(transcript)
    candidates = ranker.rank_candidates(extraction)
    enriched = ranker.attach_related_entities(candidates)
    filtered = engine.apply_rules(extraction, enriched)
    return LLMSuggestResponse(extraction=extraction, candidates=filtered)


@router.post("/llm/suggest", response_model=LLMSuggestResponse)
async def suggest(payload: LLMSuggestRequest) -> LLMSuggestResponse:
    if not payload.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript required")
    return await _suggest_from_transcript(payload.transcript)


@router.post("/llm/validate", response_model=ValidationResult)
async def validate(payload: ValidationRequest) -> ValidationResult:
    return engine.validate_candidate(payload.candidate, payload.extraction)


async def suggest_for_ws(transcript: str) -> LLMSuggestResponse:
    return await _suggest_from_transcript(transcript)
