"""LLM provider integration for structured extraction and suggestions."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from ...config import settings
from ...schemas import ExtractionExtras, LLMExtractResponse

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
    verify = settings.ssl_ca_bundle if settings.ssl_ca_bundle else True
    async with httpx.AsyncClient(timeout=30.0, verify=verify) as client:
        response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAI error %s: %s", exc.response.status_code, exc.response.text)
            raise HTTPException(status_code=502, detail="LLM provider error") from exc
    data = response.json()
    message = data["choices"][0]["message"]["content"]
    return json.loads(message)


def _mock_extract(transcript: str) -> LLMExtractResponse:
    text = transcript.strip()
    if not text:
        return LLMExtractResponse()

    sentences = [segment.strip() for segment in re.split(r"[\n\.]+", text) if segment.strip()]
    problems: list[str] = []
    procedures: list[str] = []
    negatives: list[str] = []
    participants: list[str] = []

    for sentence in sentences:
        lower = sentence.lower()
        if any(keyword in lower for keyword in ("denies", "no ", "without")):
            negatives.append(sentence)
        elif any(keyword in lower for keyword in ("performed", "procedure", "administered")):
            procedures.append(sentence)
        elif any(keyword in lower for keyword in ("patient", "mother", "father", "caregiver")):
            participants.append(sentence)
        else:
            problems.append(sentence)

    duration = None
    duration_match = re.search(r"(\d+)[\s-]*(?:minutes?|mins?)", text, re.IGNORECASE)
    if duration_match:
        duration = int(duration_match.group(1))

    setting = None
    for candidate in ("office", "hospital", "ucc", "telemedicine", "home"):
        if candidate in text.lower():
            setting = candidate
            break

    extras = ExtractionExtras()
    if re.search(r"after[-\s]?hours|evening|night", text, re.IGNORECASE):
        extras.after_hours = True
    if re.search(r"complex|extensive|difficult", text, re.IGNORECASE):
        extras.complexity = "moderate"

    return LLMExtractResponse(
        problems=problems,
        procedures=procedures,
        duration_minutes=duration,
        setting=setting,
        visit_type_hint=None,
        participants=participants,
        negatives=negatives,
        extras=extras,
    )


async def extract(transcript: str) -> LLMExtractResponse:
    provider = settings.llm_provider.lower()
    if provider == "mock":
        return _mock_extract(transcript)
    if provider != "openai":
        raise HTTPException(status_code=501, detail=f"LLM provider '{settings.llm_provider}' not supported")
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
