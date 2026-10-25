from __future__ import annotations

import re
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import yaml

from .models import BuiltEntry, Category, KBRow, RiskLevel

PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Z][A-Z0-9_]*)\s*\}\}")
CLAIM_WORDS = (
    "guarantee",
    "guaranteed",
    "100%",
    "AICTE",
    "UGC",
    "NSDC",
    "government",
    "approved",
    "accredited",
    "recognised",
    "placement assured",
    "stipend",
    "job offer",
)
CLAIM_PLACEHOLDER_PARTS = (
    "AICTE", "UGC", "NSDC", "GOVERNMENT", "APPROV", "ACCREDIT",
    "RECOGN", "GUARANTEE", "PLACEMENT_ASSURED", "STIPEND", "JOB_OFFER",
)
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")


def _read_fact_map(path: Path, *, verified: bool) -> dict[str, tuple[str, bool]]:
    if not path.exists():
        raise ValueError(f"fact file is missing: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name} must contain a YAML mapping")
    mapping = raw.get("verified_facts", raw) if verified else raw
    if not isinstance(mapping, dict):
        raise ValueError(f"{path.name} fact values must be a YAML mapping")
    result: dict[str, tuple[str, bool]] = {}
    for key, item in mapping.items():
        if isinstance(item, dict):
            value = item.get("value")
            marked_mock = bool(item.get("mock", False))
        else:
            value = item
            marked_mock = False
        if value is None or str(value).strip() == "":
            continue
        if verified and marked_mock:
            raise ValueError(f"{path.name}: verified fact {key} cannot be marked mock")
        result[str(key)] = (str(value).strip(), marked_mock or not verified)
    return result


def _normalise_question(question: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", question.casefold()).strip()


def _row_literal(answer: str) -> str:
    return PLACEHOLDER_RE.sub(" ", answer)


def validate_and_render(
    rows: list[KBRow],
    verified_path: Path,
    mock_path: Path,
    *,
    today: date | None = None,
) -> tuple[list[BuiltEntry], list[str], list[str]]:
    today = today or date.today()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        verified = _read_fact_map(verified_path, verified=True)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [], [f"verified_facts.yaml: {exc}"], warnings
    try:
        mock = _read_fact_map(mock_path, verified=False)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [], [f"mock_defaults.yaml: {exc}"], warnings

    seen_ids: set[str] = set()
    seen_questions: list[tuple[str, str]] = []
    categories = Counter(row.category.value for row in rows)
    entries: list[BuiltEntry] = []

    for row in rows:
        prefix = row.id
        if row.id in seen_ids:
            errors.append(f"{prefix}: duplicate id")
        seen_ids.add(row.id)

        normalized = _normalise_question(row.question)
        for other_id, other_question in seen_questions:
            ratio = SequenceMatcher(None, normalized, other_question).ratio()
            if normalized == other_question or ratio >= 0.92:
                errors.append(f"{prefix}: question is duplicate or near-duplicate of {other_id}")
                break
        seen_questions.append((row.id, normalized))

        if row.last_reviewed > today:
            errors.append(f"{prefix}: last_reviewed is in the future")
        variants = [part.strip() for part in row.hinglish_variants.split("|") if part.strip()]
        if len(variants) < 3:
            errors.append(f"{prefix}: requires at least 3 Hinglish variants")
        keywords = [part.strip() for part in row.keywords.split(",") if part.strip()]
        if len(keywords) < 4:
            errors.append(f"{prefix}: requires at least 4 keywords")
        if row.risk_level == RiskLevel.high and not row.handoff_offer:
            errors.append(f"{prefix}: high risk requires handoff_offer=true")
        if row.risk_level == RiskLevel.high and not (
            row.handoff_offer or row.escalate_if_unmatched
        ):
            warnings.append(f"{prefix}: high risk entry has no escalation or handoff path")

        literal = _row_literal(row.answer)
        for claim in CLAIM_WORDS:
            if re.search(rf"(?<!\w){re.escape(claim)}(?!\w)", literal, re.IGNORECASE):
                errors.append(f"{prefix}: claim word {claim!r} must be supplied by a verified placeholder")
        if URL_RE.search(literal):
            errors.append(f"{prefix}: URL literals must be placeholders")
        if EMAIL_RE.search(literal):
            errors.append(f"{prefix}: email literals must be placeholders")
        if PHONE_RE.search(literal):
            errors.append(f"{prefix}: phone literals must be placeholders")

        keys = sorted(set(PLACEHOLDER_RE.findall(row.answer)))
        unresolved_tokens = re.findall(r"\{\{[^{}]*\}\}", row.answer)
        if len(unresolved_tokens) != len(PLACEHOLDER_RE.findall(row.answer)):
            errors.append(f"{prefix}: malformed placeholder")

        rendered = row.answer
        verified_keys: list[str] = []
        mock_keys: list[str] = []
        missing_keys: list[str] = []
        for key in keys:
            resolved = verified.get(key)
            if resolved is not None:
                value, is_mock = resolved
                if is_mock:
                    mock_keys.append(key)
                else:
                    verified_keys.append(key)
            else:
                fallback = mock.get(key)
                if fallback is None:
                    missing_keys.append(key)
                    continue
                value, _ = fallback
                mock_keys.append(key)
            rendered = re.sub(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", value, rendered)
            if key in mock_keys and any(part in key.upper() for part in CLAIM_PLACEHOLDER_PARTS):
                warnings.append(
                    f"{prefix}: claim-type placeholder {key} uses MOCK data; verify before go-live"
                )

        if missing_keys:
            errors.append(f"{prefix}: missing fact key(s): {', '.join(missing_keys)}")
            continue
        is_mock = bool(mock_keys)
        if is_mock:
            rendered = f"SAMPLE DATA — {rendered}"
        if len(rendered) > 500:
            errors.append(f"{prefix}: rendered answer is {len(rendered)} characters (maximum 500)")

        if row.answer_hinglish:
            if len(row.answer_hinglish) > 500:
                errors.append(f"{prefix}: Hinglish answer exceeds 500 characters")
            if is_mock and "SAMPLE DATA" not in row.answer_hinglish:
                errors.append(f"{prefix}: mock Hinglish answer must preserve SAMPLE DATA")
        entries.append(
            BuiltEntry(
                id=row.id,
                category=row.category,
                question=row.question,
                answer_template=row.answer,
                answer_rendered=rendered,
                answer_hinglish=(row.answer_hinglish or "").strip() or None,
                hinglish_variants=variants,
                keywords=keywords,
                risk_level=row.risk_level,
                handoff_offer=row.handoff_offer,
                escalate_if_unmatched=row.escalate_if_unmatched,
                owner=row.owner,
                last_reviewed=row.last_reviewed,
                facts_required=keys,
                facts_verified=sorted(verified_keys),
                facts_mock=sorted(mock_keys),
                is_mock=is_mock,
            )
        )

    for category in Category:
        count = categories.get(category.value, 0)
        if count < 4:
            warnings.append(f"{category.value}: only {count} KB entries (recommended minimum: 4)")

    return entries, errors, warnings
