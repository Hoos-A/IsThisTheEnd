"""CSV-backed in-memory storage and lightweight retrieval indexes."""
from __future__ import annotations

import csv
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class HSC:
    code: str
    description: str
    section: str
    rate_cad: str
    notes: str
    place_of_service: List[str]
    effective_date: str
    expiry_date: str


@dataclass
class Modifier:
    code: str
    description: str
    explicit_or_implicit: str
    units_hint: str


@dataclass
class ICD9:
    code: str
    description: str
    chapter: str
    block: str


@dataclass
class SearchHit:
    domain: str
    code: str
    title: str
    snippet: str
    score: float


hsc_by_code: Dict[str, HSC] = {}
mod_by_code: Dict[str, Modifier] = {}
icd_by_code: Dict[str, ICD9] = {}

_inverted_index: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)
_last_loaded_at: Optional[float] = None


class MissingDataError(RuntimeError):
    """Raised when CSV files are missing."""


REQUIRED_FILES = {
    "somb_extracted.csv": (
        "code",
        "hsc_description",
        "section",
        "rate_cad",
        "notes",
        "place_of_service",
        "effective_date",
        "expiry_date",
    ),
    "modifiers_extracted.csv": (
        "modifier_code",
        "description",
        "explicit_or_implicit",
        "units_hint",
    ),
    "diagnostic_codes_extracted.csv": (
        "icd9",
        "description",
        "chapter",
        "block",
    ),
}


def _tokenize(text: str) -> List[str]:
    import re

    return [token for token in re.split(r"[^A-Za-z0-9.]+", text.lower()) if token]


def _clear_indexes() -> None:
    hsc_by_code.clear()
    mod_by_code.clear()
    icd_by_code.clear()
    _inverted_index.clear()


def _read_csv(path: Path) -> Iterable[Dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield {k: (v.strip() if isinstance(v, str) else "") for k, v in row.items()}


def _index_tokens(domain: str, code: str, text: str) -> None:
    for token in _tokenize(text):
        _inverted_index[token].add((domain, code))


def load_all_from_csv(data_dir: Path) -> Dict[str, int]:
    """Load CSV data and build retrieval indexes."""

    missing_files = [name for name in REQUIRED_FILES if not (data_dir / name).exists()]
    if missing_files:
        raise MissingDataError(
            "Upload CSVs to /data (see README: column names). Missing: "
            + ", ".join(missing_files)
        )

    start_time = time.time()
    _clear_indexes()

    for file_name, columns in REQUIRED_FILES.items():
        path = data_dir / file_name
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            try:
                headers = next(reader)
            except StopIteration as exc:  # pragma: no cover - defensive
                raise MissingDataError(f"{file_name} is empty") from exc
        missing_columns = [col for col in columns if col not in headers]
        if missing_columns:
            raise MissingDataError(
                f"{file_name} is missing columns: {', '.join(missing_columns)}"
            )

    for row in _read_csv(data_dir / "somb_extracted.csv"):
        code = row.get("code", "").upper()
        if not code:
            continue
        hsc = HSC(
            code=code,
            description=row.get("hsc_description", ""),
            section=row.get("section", ""),
            rate_cad=row.get("rate_cad", ""),
            notes=row.get("notes", ""),
            place_of_service=[part.strip() for part in row.get("place_of_service", "").split(",") if part.strip()],
            effective_date=row.get("effective_date", ""),
            expiry_date=row.get("expiry_date", ""),
        )
        hsc_by_code[code] = hsc
        _index_tokens("hsc", code, f"{hsc.description} {hsc.notes} {hsc.section}")

    for row in _read_csv(data_dir / "modifiers_extracted.csv"):
        code = row.get("modifier_code", "").upper()
        if not code:
            continue
        mod = Modifier(
            code=code,
            description=row.get("description", ""),
            explicit_or_implicit=row.get("explicit_or_implicit", ""),
            units_hint=row.get("units_hint", ""),
        )
        mod_by_code[code] = mod
        _index_tokens("modifier", code, mod.description)

    for row in _read_csv(data_dir / "diagnostic_codes_extracted.csv"):
        code = row.get("icd9", "").upper()
        if not code:
            continue
        icd = ICD9(
            code=code,
            description=row.get("description", ""),
            chapter=row.get("chapter", ""),
            block=row.get("block", ""),
        )
        icd_by_code[code] = icd
        _index_tokens("icd9", code, icd.description)

    global _last_loaded_at
    _last_loaded_at = time.time()
    duration = _last_loaded_at - start_time
    logger.info(
        "Loaded %s HSC / %s Modifiers / %s ICD9 in %.3fs",
        len(hsc_by_code),
        len(mod_by_code),
        len(icd_by_code),
        duration,
    )
    logger.info("CSV indexes: OK")

    return {
        "hsc": len(hsc_by_code),
        "modifiers": len(mod_by_code),
        "icd9": len(icd_by_code),
    }


def reload_all(data_dir: Path, force: bool = False) -> Dict[str, int]:
    if not force and _last_loaded_at:
        return {
            "hsc": len(hsc_by_code),
            "modifiers": len(mod_by_code),
            "icd9": len(icd_by_code),
        }
    return load_all_from_csv(data_dir)


def search(text: str, limit: int = 20) -> List[SearchHit]:
    if not text.strip():
        return []

    scores: MutableMapping[Tuple[str, str], float] = defaultdict(float)
    for token in _tokenize(text):
        for domain, code in _inverted_index.get(token, set()):
            weight = 2.0 if domain == "hsc" else 1.0
            scores[(domain, code)] += weight

    def build_hit(domain: str, code: str, score: float) -> Optional[SearchHit]:
        if domain == "hsc":
            hsc = hsc_by_code.get(code)
            if not hsc:
                return None
            return SearchHit(domain, code, hsc.description, hsc.notes, score)
        if domain == "modifier":
            mod = mod_by_code.get(code)
            if not mod:
                return None
            return SearchHit(domain, code, mod.description, "", score)
        if domain == "icd9":
            icd = icd_by_code.get(code)
            if not icd:
                return None
            return SearchHit(domain, code, icd.description, icd.block, score)
        return None

    hits = [build_hit(domain, code, score) for (domain, code), score in scores.items()]
    filtered = [hit for hit in hits if hit is not None]
    filtered.sort(key=lambda h: h.score, reverse=True)
    return filtered[:limit]


def get_last_loaded_at() -> Optional[float]:
    return _last_loaded_at
