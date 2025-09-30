"""Search endpoints leveraging CSV indexes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..csv_store import MissingDataError, search
from ..schemas import SearchResult

router = APIRouter(prefix="", tags=["search"])


@router.get("/search", response_model=list[SearchResult])
async def search_endpoint(q: str = Query(..., min_length=1)) -> list[SearchResult]:
    try:
        hits = search(q)
    except MissingDataError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=503, detail=str(exc))
    return [
        SearchResult(domain=hit.domain, code=hit.code, title=hit.title, snippet=hit.snippet, score=hit.score)
        for hit in hits
    ]
