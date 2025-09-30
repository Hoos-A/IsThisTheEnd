"""OpenAI Whisper transcription relay."""
from __future__ import annotations

import logging
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from ...config import settings

logger = logging.getLogger(__name__)


async def transcribe(audio_bytes: bytes, sample_rate: int, encoding: str) -> Dict[str, Any]:
    if not audio_bytes:
        return {"text": "", "segments": []}
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Set Codespaces Secret OPENAI_API_KEY")

    base_url = settings.openai_api_base or "https://api.openai.com/v1"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    files = {
        "file": ("audio.wav", audio_bytes, "application/octet-stream"),
    }
    data = {
        "model": settings.openai_model_stt,
        "response_format": "verbose_json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/audio/transcriptions",
            headers=headers,
            data=data,
            files=files,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Whisper error %s: %s", exc.response.status_code, exc.response.text)
            raise HTTPException(status_code=502, detail="STT provider error") from exc
    return response.json()
