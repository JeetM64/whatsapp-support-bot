from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

from .composer import compose
from .config import RagConfig, load_dotenv
from .decision import compose_clarification, decide, no_match_reply
from .models import Decision, EntryRef, RagResult, TokenUsage, VerifierReport
from .normalize import detect_language
from .providers import NoneProvider, Provider, create_provider
from .retriever import ChromaStorageBusy, RetrievalOutput, Retriever

LOGGER = logging.getLogger("customer_support.rag")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ().-]{8,}\d)(?!\d)")
OTP_RE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")


def mask_pii(text: str) -> str:
    masked = EMAIL_RE.sub("[EMAIL]", text)
    masked = CARD_RE.sub("[CARD]", masked)
    masked = PHONE_RE.sub("[PHONE]", masked)
    return OTP_RE.sub("[CODE]", masked)


def _cost(provider: Provider, usage: TokenUsage, config: RagConfig) -> float | str:
    if isinstance(provider, NoneProvider):
        return 0.0
    prices = config.pricing.get(getattr(provider, "name", ""), {})
    input_price = prices.get("input_per_million_usd")
    output_price = prices.get("output_per_million_usd")
    if (
        input_price is None
        or output_price is None
        or usage.input_tokens is None
        or usage.output_tokens is None
    ):
        return "unknown"
    return (
        usage.input_tokens * float(input_price)
        + usage.output_tokens * float(output_price)
    ) / 1_000_000


def _refs(retrieval: RetrievalOutput | None, limit: int = 3) -> list[EntryRef]:
    if retrieval is None:
        return []
    return [
        EntryRef(id=item.id, category=item.category, is_mock=item.is_mock)
        for item in retrieval.candidates[:limit]
    ]


class RagEngine:
    def __init__(
        self,
        root: Path | None = None,
        *,
        provider: Provider | None = None,
        retriever: Retriever | None = None,
    ) -> None:
        self.root = (root or Path.cwd()).resolve()
        self.config = RagConfig.load(self.root)
        load_dotenv(self.root)
        self._init_error: Exception | None = None
        try:
            self.provider = provider or create_provider(
                None, max_tokens=int(self.config.provider.get("max_tokens", 256))
            )
        except Exception as exc:
            self.provider = NoneProvider()
            self._init_error = exc
        try:
            self.retriever = retriever or Retriever(self.root, self.config)
        except Exception as exc:
            self._init_error = self._init_error or exc
            self.retriever = None

    def answer(self, message: str, session: dict | None = None) -> RagResult:
        started = time.perf_counter()
        language = detect_language(message)
        retrieval: RetrievalOutput | None = None
        try:
            if self._init_error is not None or self.retriever is None:
                raise self._init_error or RuntimeError("retriever unavailable")
            retrieval = self.retriever.retrieve(message)
            decision = decide(message, retrieval, self.retriever.entries, self.config)
            refs = _refs(retrieval)
            if decision.decision == Decision.NO_MATCH:
                reply = no_match_reply()
                mode = "fallback"
                verifier = VerifierReport(
                    passed=True,
                    checks={"no_match_fallback": True, "no_sensitive_content": True},
                    fallback_used=False,
                )
                usage = TokenUsage()
            elif decision.decision == Decision.CLARIFY:
                reply = compose_clarification(
                    language, decision.candidate_ids, self.retriever.entries
                )
                mode = "extractive"
                verifier = VerifierReport(
                    passed=True,
                    checks={"clarification_derived_from_candidates": True},
                    fallback_used=False,
                )
                usage = TokenUsage()
            else:
                selected_ids = decision.candidate_ids[:2] or [retrieval.candidates[0].id]
                selected_entries = [
                    self.retriever.entries[entry_id] for entry_id in selected_ids
                ]
                composition = compose(
                    message,
                    language,
                    selected_entries,
                    self.provider,
                    self.config,
                    self.retriever.embedder,
                )
                reply = composition.reply
                mode = composition.mode
                verifier = composition.verifier
                usage = composition.usage
                refs = [
                    EntryRef(
                        id=entry["id"],
                        category=str(entry["category"]),
                        is_mock=bool(entry["is_mock"]),
                    )
                    for entry in selected_entries
                ]
            LOGGER.info(
                "rag_answer decision=%s reason=%s confidence=%.3f mode=%s degraded=%s query=%s",
                decision.decision.value,
                decision.reason_code,
                decision.confidence,
                mode,
                retrieval.degraded,
                mask_pii(message),
            )
            return RagResult(
                decision=decision.decision,
                reason_code=decision.reason_code,
                confidence=decision.confidence,
                entries=refs,
                reply=reply,
                mode=mode,
                degraded=retrieval.degraded,
                verifier=verifier,
                language=language,
                latency_ms=(time.perf_counter() - started) * 1000,
                usage=usage,
                estimated_cost_usd=_cost(self.provider, usage, self.config),
            )
        except Exception as exc:
            error_name = type(exc).__name__
            if isinstance(exc, ChromaStorageBusy):
                reason = "storage_busy"
                LOGGER.error("%s query=%s", str(exc), mask_pii(message))
            else:
                reason = "internal_error"
                LOGGER.exception(
                    "RAG internal error type=%s query=%s",
                    error_name,
                    mask_pii(message),
                )
            return RagResult(
                decision=Decision.NO_MATCH,
                reason_code=reason,
                confidence=0.0,
                entries=_refs(retrieval),
                reply=no_match_reply(),
                mode="fallback",
                degraded=True,
                verifier=VerifierReport(
                    passed=False,
                    checks={"internal_error": False},
                    failures=[reason],
                    fallback_used=True,
                ),
                language=language,
                latency_ms=(time.perf_counter() - started) * 1000,
                usage=TokenUsage(),
                estimated_cost_usd="unknown",
            )
