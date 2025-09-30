"""Pydantic models for request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ProviderStatus(BaseModel):
    stt: str
    llm: str


class Counts(BaseModel):
    hsc: int = 0
    modifiers: int = 0
    icd9: int = 0


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded", "error"]
    details: List[str] = Field(default_factory=list)
    providers: ProviderStatus
    counts: Counts
    data_dir: str


class SearchResult(BaseModel):
    domain: Literal["hsc", "modifier", "icd9"]
    code: str
    title: str
    snippet: str
    score: float


class LLMExtractRequest(BaseModel):
    transcript: str = Field("", description="Raw transcript text from STT")


class ExtractionExtras(BaseModel):
    after_hours: Optional[bool] = None
    complexity: Optional[Literal["low", "moderate", "high"]] = None


class LLMExtractResponse(BaseModel):
    problems: List[str] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    duration_minutes: Optional[int] = None
    setting: Optional[str] = None
    visit_type_hint: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    negatives: List[str] = Field(default_factory=list)
    extras: ExtractionExtras = Field(default_factory=ExtractionExtras)


class LLMSuggestRequest(BaseModel):
    transcript: str
    manual_context: Optional[Dict[str, str]] = None


class CandidateModifier(BaseModel):
    code: str
    description: str
    units: Optional[float] = None


class CandidateDiagnosis(BaseModel):
    code: str
    description: str


class CodeCandidate(BaseModel):
    hsc_code: str
    description: str
    score: float
    why: List[str]
    citations: List[str]
    modifiers: List[CandidateModifier] = Field(default_factory=list)
    diagnoses: List[CandidateDiagnosis] = Field(default_factory=list)
    notes: Optional[str] = None


class LLMSuggestResponse(BaseModel):
    extraction: LLMExtractResponse
    candidates: List[CodeCandidate]


class ValidationItem(BaseModel):
    level: Literal["info", "warning", "error"]
    message: str


class ValidationResult(BaseModel):
    ok: bool
    items: List[ValidationItem] = Field(default_factory=list)


class ValidationRequest(BaseModel):
    candidate: CodeCandidate
    extraction: LLMExtractResponse


class WsSttPartial(BaseModel):
    text: str
    startMs: int
    endMs: int


class WsSttFinal(WsSttPartial):
    pass


class WsCodesUpdate(BaseModel):
    candidates: List[CodeCandidate]
    rationale: str
    latencyMs: int
    generatedAt: datetime = Field(default_factory=datetime.utcnow)
