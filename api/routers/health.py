"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import csv_store
from ..config import settings
from ..schemas import Counts, HealthStatus, ProviderStatus

router = APIRouter(prefix="", tags=["health"])


@router.get("/health", response_model=HealthStatus)
async def get_health() -> HealthStatus:
    counts = Counts(
        hsc=len(csv_store.hsc_by_code),
        modifiers=len(csv_store.mod_by_code),
        icd9=len(csv_store.icd_by_code),
    )
    ok = bool(counts.hsc and counts.modifiers and counts.icd9)
    message = None
    if settings.require_openai_key and not settings.openai_api_key:
        message = "Set Codespaces Secret OPENAI_API_KEY"
        ok = False
    if not ok and not csv_store.hsc_by_code:
        message = "Upload CSVs to /data (see README: column names)."
    if not ok:
        raise HTTPException(status_code=503, detail=message or "Service unavailable")
    return HealthStatus(
        ok=True,
        providers=ProviderStatus(stt=settings.stt_provider, llm=settings.llm_provider),
        counts=counts,
        data_dir=str(settings.data_dir),
    )
