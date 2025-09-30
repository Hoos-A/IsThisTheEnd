"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import csv_store
from .config import settings
from .routers import admin, health, llm_codes, search, stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AHS Billing Assistant", version="0.1.0")

origins = ["http://localhost:5173", "https://*.github.dev"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(admin.router)
app.include_router(search.router)
app.include_router(llm_codes.router)
app.include_router(stream.router)


@app.on_event("startup")
async def startup_event() -> None:
    if settings.require_openai_key and not settings.openai_api_key:
        logger.error("OPENAI_API_KEY missing. Set Codespaces Secret OPENAI_API_KEY")
        raise RuntimeError("Set Codespaces Secret OPENAI_API_KEY")
    try:
        counts = csv_store.load_all_from_csv(settings.data_dir)
    except csv_store.MissingDataError as exc:
        logger.error(str(exc))
        raise RuntimeError(str(exc))
    logger.info(
        "Startup complete — loaded %s HSC / %s Modifiers / %s ICD9 — CSV indexes: OK",
        counts["hsc"],
        counts["modifiers"],
        counts["icd9"],
    )


@app.get("/")
async def root() -> dict:
    return {"message": "AHS Billing Assistant API"}
