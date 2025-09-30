"""Administrative endpoints for CSV management."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, Query

from .. import csv_store
from ..config import settings
from ..schemas import Counts

router = APIRouter(prefix="", tags=["admin"])


@router.get("/data/status")
async def data_status() -> dict:
    return {
        "counts": Counts(
            hsc=len(csv_store.hsc_by_code),
            modifiers=len(csv_store.mod_by_code),
            icd9=len(csv_store.icd_by_code),
        ),
        "last_loaded_at": csv_store.get_last_loaded_at(),
        "data_dir": str(settings.data_dir),
    }


@router.post("/admin/reload")
async def reload_data(force: bool = Query(default=False)) -> dict:
    try:
        counts = csv_store.reload_all(settings.data_dir, force=force)
    except csv_store.MissingDataError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"counts": counts, "forced": force, "timestamp": dt.datetime.utcnow().isoformat()}
