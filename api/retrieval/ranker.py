"""Simple token-based retrieval and ranking for HSC suggestions."""
from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Tuple

from .. import csv_store
from ..schemas import CandidateDiagnosis, CandidateModifier, CodeCandidate, LLMExtractResponse


def _collect_tokens(extraction: LLMExtractResponse) -> List[str]:
    tokens: List[str] = []
    for field in (
        extraction.problems,
        extraction.procedures,
        extraction.participants,
        extraction.negatives,
    ):
        for entry in field:
            tokens.extend(csv_store._tokenize(entry))  # type: ignore[attr-defined]
    for optional_text in (extraction.setting, extraction.visit_type_hint):
        if optional_text:
            tokens.extend(csv_store._tokenize(optional_text))  # type: ignore[attr-defined]
    return [token for token in tokens if token]


def rank_candidates(
    extraction: LLMExtractResponse, max_candidates: int = 10
) -> List[CodeCandidate]:
    if not csv_store.hsc_by_code:
        return []
    query_tokens = _collect_tokens(extraction)
    if not query_tokens:
        return []

    combined_hits = csv_store.search(" ".join(query_tokens), limit=50)
    counter = Counter()
    for hit in combined_hits:
        if hit.domain != "hsc":
            continue
        counter[hit.code] += hit.score

    ranked: List[Tuple[str, float]] = counter.most_common(max_candidates)
    candidates: List[CodeCandidate] = []
    for code, score in ranked:
        hsc = csv_store.hsc_by_code.get(code)
        if not hsc:
            continue
        citations = [f"HSC:{code}"]
        why = list({token for token in query_tokens if token in hsc.description.lower()})
        candidates.append(
            CodeCandidate(
                hsc_code=code,
                description=hsc.description,
                score=float(score),
                why=why or ["token match"],
                citations=citations,
                modifiers=[],
                diagnoses=[],
                notes=hsc.notes,
            )
        )
    return candidates


def attach_related_entities(candidates: Iterable[CodeCandidate]) -> List[CodeCandidate]:
    enriched: List[CodeCandidate] = []
    for candidate in candidates:
        base = candidate.model_copy(deep=True)
        # naive heuristics: attach modifiers and diagnoses with overlapping tokens
        tokens = set(csv_store._tokenize(candidate.description))  # type: ignore[attr-defined]
        related_mods: List[CandidateModifier] = []
        for mod in csv_store.mod_by_code.values():
            if tokens & set(csv_store._tokenize(mod.description)):  # type: ignore[attr-defined]
                related_mods.append(
                    CandidateModifier(code=mod.code, description=mod.description)
                )
                if len(related_mods) >= 3:
                    break
        related_dx: List[CandidateDiagnosis] = []
        for icd in csv_store.icd_by_code.values():
            if tokens & set(csv_store._tokenize(icd.description)):  # type: ignore[attr-defined]
                related_dx.append(CandidateDiagnosis(code=icd.code, description=icd.description))
                if len(related_dx) >= 3:
                    break
        base.modifiers = related_mods
        base.diagnoses = related_dx
        enriched.append(base)
    return enriched
