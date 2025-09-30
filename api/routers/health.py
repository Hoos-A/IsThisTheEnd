"""Health and readiness endpoints."""
from __future__ import annotations

from typing import Literal, cast

from fastapi import APIRouter

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
    issues: list[str] = []

    if not counts.hsc or not counts.modifiers or not counts.icd9:
        issues.append("Upload CSVs to /data (see README: column names).")

    if settings.require_openai_key and not settings.openai_api_key:
        issues.append("Set Codespaces Secret OPENAI_API_KEY")

    status: str
    if not issues:
        status = "ok"
    elif counts.hsc and counts.modifiers and counts.icd9:
        status = "degraded"
    else:
        status = "error"

    literal_status = cast(Literal["ok", "degraded", "error"], status)

    return HealthStatus(
        status=literal_status,
        details=issues,
        providers=ProviderStatus(stt=settings.stt_provider, llm=settings.llm_provider),
        counts=counts,
        data_dir=str(settings.data_dir),
    )
