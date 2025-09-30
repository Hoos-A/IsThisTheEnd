"""LLM provider integration for structured extraction and suggestions."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from ...config import settings
from ...schemas import LLMExtractResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You assist with structured extraction for Alberta SOMB physician billing.\n"
    "Return ONLY strict JSON with keys:\n"
    "problems[], procedures[], duration_minutes, setting, visit_type_hint,\n"
    "participants[], negatives[], extras{ after_hours?: boolean, complexity?: \"low\"|\"moderate\"|\"high\" }.\n"
    "Be conservative: if unsure, return null/empty values. No identifiers or quotes. Use only the provided text."
)


async def _call_openai(messages: list[dict[str, str]]) -> Dict[str, Any]:
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Set Codespaces Secret OPENAI_API_KEY")

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    base_url = settings.openai_api_base or "https://api.openai.com/v1"
    payload = {
        "model": settings.openai_model_llm,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 500,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAI error %s: %s", exc.response.status_code, exc.response.text)
            raise HTTPException(status_code=502, detail="LLM provider error") from exc
    data = response.json()
    message = data["choices"][0]["message"]["content"]
    return json.loads(message)


async def extract(transcript: str) -> LLMExtractResponse:
    if not transcript.strip():
        return LLMExtractResponse()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": transcript[:3000]},
    ]
    try:
        payload = await _call_openai(messages)
        return LLMExtractResponse.model_validate(payload)
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("LLM payload error: %s", exc)
        raise HTTPException(status_code=502, detail="Invalid LLM response") from exc
