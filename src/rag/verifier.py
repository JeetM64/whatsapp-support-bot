from __future__ import annotations

import re
from typing import Any

from .config import RagConfig
from .embeddings import Embedder, cosine_similarity
from .models import LLMReply, VerifierReport
from .normalize import detect_language

CLAIM_WORDS = (
    "guarantee",
    "guaranteed",
    "100%",
    "AICTE",
    "UGC",
    "NSDC",
    "ISO",
    "government",
    "approved",
    "accredited",
    "recognised",
    "assured",
    "stipend",
    "job offer",
)
COMMITMENTS = (
    "we will refund",
    "i will refund",
    "will be refunded",
    "refund will be",
    "refund is approved",
    "i promise",
    "we promise",
    "definitely",
    "you will get",
    "you are guaranteed",
)
URL_RE = re.compile(r"https?://[^\s<>()]+|www\.[^\s<>()]+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")
CURRENCY_RE = re.compile(
    r"(?i)(?:₹|rs\.?|inr)\s*(?:\[mock\s*)?[\d,]+(?:\.\d+)?\]?"
)
DURATION_RE = re.compile(
    r"(?i)\b\d+(?:\.\d+)?\s*(?:days?|weeks?|months?|years?|hours?|hrs?|minutes?|mins?)\b"
)
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)")
MARKDOWN_RE = re.compile(r"(?m)^\s*(?:#{1,6}\s|>\s|[-*]\s|\d+\.\s)|[*_]{1,2}[^*_]+[*_]{1,2}")


def _entities(text: str) -> dict[str, set[str]]:
    def values(pattern: re.Pattern[str]) -> set[str]:
        return {match.rstrip(".,;!?") for match in pattern.findall(text)}

    return {
        "currency": values(CURRENCY_RE),
        "duration": values(DURATION_RE),
        "date": values(DATE_RE),
        "url": {value.rstrip(".,;!?)").casefold() for value in URL_RE.findall(text)},
        "email": {value.casefold() for value in EMAIL_RE.findall(text)},
        "phone": {re.sub(r"\D", "", value) for value in PHONE_RE.findall(text)},
        "number": set(NUMBER_RE.findall(text)),
    }


def verify_reply(
    candidate: LLMReply,
    selected_entries: list[dict[str, Any]],
    allowed_entry_ids: set[str],
    user_language: str,
    config: RagConfig,
    embedder: Embedder | None,
) -> VerifierReport:
    source = "\n".join(str(entry.get("answer_rendered", "")) for entry in selected_entries)
    checks: dict[str, bool] = {}
    failures: list[str] = []

    checks["entry_ids_subset"] = set(candidate.used_entry_ids).issubset(allowed_entry_ids)
    if not checks["entry_ids_subset"]:
        failures.append("used_entry_ids contains an entry outside the selected set")

    reply_entities = _entities(candidate.reply)
    source_entities = _entities(source)
    entity_failures = [
        key for key, values in reply_entities.items() if not values.issubset(source_entities[key])
    ]
    checks["entities_grounded"] = not entity_failures
    if entity_failures:
        failures.append("new or changed factual entity: " + ", ".join(entity_failures))

    claim_failures = [
        claim
        for claim in CLAIM_WORDS
        if re.search(rf"(?<!\w){re.escape(claim)}(?!\w)", candidate.reply, re.IGNORECASE)
        and not re.search(rf"(?<!\w){re.escape(claim)}(?!\w)", source, re.IGNORECASE)
    ]
    checks["claims_grounded"] = not claim_failures
    if claim_failures:
        failures.append("unsupported claim word(s): " + ", ".join(claim_failures))

    commitment_failures = [
        phrase
        for phrase in COMMITMENTS
        if phrase.casefold() in candidate.reply.casefold()
        and phrase.casefold() not in source.casefold()
    ]
    checks["commitments_grounded"] = not commitment_failures
    if commitment_failures:
        failures.append("unsupported commitment: " + ", ".join(commitment_failures))

    checks["nonempty_under_limit"] = (
        bool(candidate.reply.strip())
        and len(candidate.reply) <= int(config.decision.get("max_reply_chars", 600))
    )
    if not checks["nonempty_under_limit"]:
        failures.append("reply is empty or exceeds the configured character limit")

    checks["no_markdown"] = not bool(MARKDOWN_RE.search(candidate.reply))
    if not checks["no_markdown"]:
        failures.append("reply contains Markdown formatting")

    sample_required = any(bool(entry.get("is_mock")) for entry in selected_entries)
    checks["sample_label_preserved"] = (
        not sample_required
        or not config.sample_label_enabled
        or "SAMPLE DATA" in candidate.reply
    )
    if not checks["sample_label_preserved"]:
        failures.append("SAMPLE DATA label was removed")

    if embedder is None:
        checks["semantic_grounding"] = False
        failures.append("semantic grounding unavailable because the multilingual model is not cached")
    else:
        try:
            vectors = embedder.encode([candidate.reply, source])
            similarity = cosine_similarity(vectors[0], vectors[1])
            checks["semantic_grounding"] = similarity >= float(config.thresholds["ground"])
            if not checks["semantic_grounding"]:
                failures.append(
                    f"semantic grounding score {similarity:.3f} is below threshold "
                    f"{float(config.thresholds['ground']):.3f}"
                )
        except Exception as exc:
            checks["semantic_grounding"] = False
            failures.append(f"semantic grounding failed: {type(exc).__name__}")

    actual_language = detect_language(candidate.reply)
    checks["language_matches"] = actual_language == user_language
    if not checks["language_matches"]:
        failures.append(f"reply language {actual_language} does not match {user_language}")

    return VerifierReport(
        passed=all(checks.values()),
        checks=checks,
        failures=failures,
        fallback_used=False,
    )


def verified_extractive_reply(
    reply: str, selected_entries: list[dict[str, Any]], max_chars: int
) -> VerifierReport:
    source_answers = {str(entry.get(key, "")) for entry in selected_entries for key in ("answer_rendered", "answer_hinglish") if entry.get(key)}
    exact_source_with_handoff = False
    fee_notes = (
        "fees can change, please confirm on the official site before paying",
        "fees badal sakti hain; payment se pehle official site par confirm kar lein",
    )
    for entry in selected_entries:
        if not entry.get("handoff_offer"):
            continue
        for field, phrase in (
            ("answer_rendered", "I can connect a team member."),
            ("answer_hinglish", "Main aapko support team se connect kar sakta hoon."),
        ):
            source = str(entry.get(field, "") or "")
            if not source or phrase.casefold() in source.casefold():
                continue
            expected = source.rstrip(". ") + ". " + phrase
            fee_note = next((note for note in fee_notes if note in source.casefold()), None)
            fee_offset = source.casefold().rfind(fee_note) if fee_note else -1
            if fee_offset >= 0:
                expected = source[:fee_offset].rstrip(". ") + ". " + phrase + " " + source[fee_offset:]
            if reply == expected:
                exact_source_with_handoff = True
                break
        if exact_source_with_handoff:
            break
    checks = {
        "source_exact": bool(selected_entries)
        and (reply in source_answers or exact_source_with_handoff),
        "nonempty_under_limit": bool(reply.strip()) and len(reply) <= max_chars,
        "sample_label_preserved": not any(
            bool(entry.get("is_mock")) for entry in selected_entries
        )
        or "SAMPLE DATA" in reply,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return VerifierReport(
        passed=not failures,
        checks=checks,
        failures=failures,
        fallback_used=False,
    )
