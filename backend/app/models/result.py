from typing import Any, Optional

from pydantic import BaseModel, Field

from backend.app.core.constants import FailReason, FieldStatus, Verdict
from backend.app.models.candidate import Candidate
from backend.app.models.sku import AnalyzeRequest, ParsedIdentity


class FieldMatch(BaseModel):
    target: Optional[str] = None
    extracted: Optional[str] = None
    status: FieldStatus = FieldStatus.UNVERIFIED
    confidence: float = 0.0


class ScoreBreakdown(BaseModel):
    producer: float = 0.0
    appellation: float = 0.0
    vineyard_or_cuvee: float = 0.0
    classification: float = 0.0
    vintage: float = 0.0
    ocr_clarity: float = 0.0
    image_quality: float = 0.0
    source_trust: float = 0.0


class ModuleVote(BaseModel):
    module: str
    available: bool = True
    passed: bool = False
    confidence: float = 0.0
    weight: float = 0.0
    reason: str = ""
    field_matches: dict[str, FieldMatch] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class DebugPayload(BaseModel):
    queries: list[str] = Field(default_factory=list)
    candidates_considered: int = 0
    hard_fail_reasons: list[str] = Field(default_factory=list)
    ocr_snippets: list[str] = Field(default_factory=list)
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    notes: list[str] = Field(default_factory=list)
    candidate_summaries: list[dict[str, Any]] = Field(default_factory=list)
    module_votes: list[ModuleVote] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    input: AnalyzeRequest
    parsed_identity: ParsedIdentity
    verdict: Verdict
    confidence: float = 0.0
    selected_image_url: Optional[str] = None
    selected_source_page: Optional[str] = None
    reason: str
    fail_reason: Optional[FailReason] = None
    field_matches: dict[str, FieldMatch] = Field(default_factory=dict)
    debug: DebugPayload = Field(default_factory=DebugPayload)


class BatchAnalyzeResponse(BaseModel):
    results: list[AnalyzeResponse] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class CandidateEvaluation(BaseModel):
    candidate: Candidate
    field_matches: dict[str, FieldMatch] = Field(default_factory=dict)
    module_votes: list[ModuleVote] = Field(default_factory=list)
    fail_reason: Optional[FailReason] = None
    should_fail: bool = False
    confidence: float = 0.0
    reason: str
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
