from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Decision(str, Enum):
    ANSWER = "ANSWER"
    CLARIFY = "CLARIFY"
    NO_MATCH = "NO_MATCH"


class EntryRef(BaseModel):
    id: str
    category: str
    is_mock: bool


class Candidate(BaseModel):
    id: str
    category: str
    is_mock: bool
    rrf_score: float
    semantic_score: float
    lexical_score: float
    confidence: float


class VerifierReport(BaseModel):
    passed: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
    fallback_used: bool = False


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class RagResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision
    reason_code: str
    confidence: float = Field(ge=0.0, le=1.0)
    entries: list[EntryRef] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    reply: str
    mode: Literal["extractive", "llm", "fallback"]
    degraded: bool = False
    verifier: VerifierReport
    language: Literal["English", "Hinglish", "Hindi"]
    latency_ms: float
    timings_ms: dict[str, float] = Field(default_factory=dict)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    estimated_cost_usd: float | str = "unknown"


class LLMReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str = Field(min_length=1)
    used_entry_ids: list[str]
    language: Literal["English", "Hinglish", "Hindi"]


class QueryDecision(BaseModel):
    decision: Decision
    reason_code: str
    confidence: float = Field(ge=0.0, le=1.0)
    candidate_ids: list[str] = Field(default_factory=list)
    related_ids: list[str] = Field(default_factory=list)
