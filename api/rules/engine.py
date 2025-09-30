"""Deterministic rule evaluation for SOMB billing candidates."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Iterable, List

from .. import csv_store
from ..schemas import CodeCandidate, LLMExtractResponse, ValidationItem, ValidationResult


PLACE_OF_SERVICE_FALLBACK = {
    "office": {"office"},
    "hospital": {"hospital", "inpatient"},
    "ucc": {"ucc", "urgent care"},
    "telemedicine": {"telemedicine", "virtual"},
}


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def apply_rules(
    extraction: LLMExtractResponse, candidates: Iterable[CodeCandidate]
) -> List[CodeCandidate]:
    setting = _normalize(extraction.setting)
    filtered: List[CodeCandidate] = []
    allowed_tokens = PLACE_OF_SERVICE_FALLBACK.get(setting, {setting} if setting else set())

    for candidate in candidates:
        hsc = csv_store.hsc_by_code.get(candidate.hsc_code)
        if not hsc:
            continue
        if setting and hsc.place_of_service:
            normalized_pos = {pos.lower() for pos in hsc.place_of_service}
            if allowed_tokens and not (normalized_pos & allowed_tokens):
                continue
        filtered.append(candidate)

    return filtered


def _validate_date(date_text: str, when: str, items: List[ValidationItem]) -> None:
    if not date_text:
        return
    try:
        datetime.fromisoformat(date_text)
    except ValueError:
        items.append(ValidationItem(level="warning", message=f"{when} date '{date_text}' not ISO format"))


def _validate_after_hours(candidate: CodeCandidate, extraction: LLMExtractResponse, items: List[ValidationItem]) -> None:
    if candidate.hsc_code == "03.01AA" and extraction.duration_minutes:
        units = math.ceil(extraction.duration_minutes / 15)
        if candidate.modifiers:
            candidate.modifiers[0].units = units
        items.append(
            ValidationItem(
                level="info",
                message=f"03.01AA duration {extraction.duration_minutes} minutes ⇒ {units} units",
            )
        )


def validate_candidate(candidate: CodeCandidate, extraction: LLMExtractResponse) -> ValidationResult:
    items: List[ValidationItem] = []
    hsc = csv_store.hsc_by_code.get(candidate.hsc_code)
    if not hsc:
        return ValidationResult(ok=False, items=[ValidationItem(level="error", message="Unknown HSC code")])

    _validate_date(hsc.effective_date, "Effective", items)
    _validate_date(hsc.expiry_date, "Expiry", items)

    setting = _normalize(extraction.setting)
    if setting and hsc.place_of_service:
        normalized_pos = {pos.lower() for pos in hsc.place_of_service}
        allowed_tokens = PLACE_OF_SERVICE_FALLBACK.get(setting, {setting})
        if allowed_tokens and not (normalized_pos & allowed_tokens):
            items.append(
                ValidationItem(
                    level="error",
                    message=f"Setting '{setting}' not permitted for {candidate.hsc_code}",
                )
            )

    _validate_after_hours(candidate, extraction, items)

    ok = not any(item.level == "error" for item in items)
    return ValidationResult(ok=ok, items=items)
