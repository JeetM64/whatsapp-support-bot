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
    "ISO",
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
    "RECOGN", "GUARANTEE", "PLACEMENT_ASSURED", "STIPEND", "JOB_OFFER", "ISO",
)
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")


def _read_fact_map(path: Path, *, verified: bool) -> dict[str, tuple[str, bool, str, str]]:
    if not path.exists():
        raise ValueError(f"fact file is missing: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name} must contain a YAML mapping")
    if verified:
        fact_data = raw.get("verified_facts", raw)
        if isinstance(fact_data, dict) and "facts" in fact_data:
            facts = fact_data.get("facts")
            if not isinstance(facts, list):
                raise ValueError(f"{path.name}: facts must be a list")
            fact_ids: set[str] = set()
            for index, fact in enumerate(facts, start=1):
                if not isinstance(fact, dict):
                    raise ValueError(f"{path.name}: fact entry #{index} must be a mapping")
                missing = {"id", "text", "source", "retrieved", "confidence"} - set(fact)
                if missing:
                    raise ValueError(f"{path.name}: fact entry #{index} is missing {', '.join(sorted(missing))}")
                fact_id = fact["id"]
                if not isinstance(fact_id, str) or not fact_id.strip():
                    raise ValueError(f"{path.name}: fact entry #{index} has missing or unusable id")
                if fact["confidence"] not in {"high", "medium", "low"}:
                    raise ValueError(f"{path.name}: fact {fact_id} has invalid confidence")
                fact_ids.add(fact_id.strip())
            policies = fact_data.get("policies", [])
            if not isinstance(policies, list):
                raise ValueError(f"{path.name}: policies must be a list")
            for index, policy in enumerate(policies, start=1):
                if not isinstance(policy, dict):
                    raise ValueError(f"{path.name}: policy entry #{index} must be a mapping")
                missing = {"id", "text", "source", "retrieved", "confidence"} - set(policy)
                if missing:
                    raise ValueError(f"{path.name}: policy entry #{index} is missing {', '.join(sorted(missing))}")
                policy_id = policy["id"]
                if not isinstance(policy_id, str) or not policy_id.strip():
                    raise ValueError(f"{path.name}: policy entry #{index} has missing or unusable id")
                if policy["confidence"] not in {"high", "medium", "low"}:
                    raise ValueError(f"{path.name}: policy {policy_id} has invalid confidence")
                fact_ids.add(policy_id.strip())
        mapping = fact_data.get("placeholders", fact_data) if isinstance(fact_data, dict) else fact_data
    else:
        mapping = raw
    if not isinstance(mapping, dict):
        raise ValueError(f"{path.name} fact values must be a YAML mapping")
    if verified and isinstance(fact_data, dict) and "facts" in fact_data:
        for key, item in mapping.items():
            if not isinstance(item, dict):
                raise ValueError(f"{path.name}: placeholder {key} must map to a value and fact reference")
            references = item.get("facts", item.get("fact"))
            if isinstance(references, str):
                references = [references]
            if not isinstance(references, list) or not references:
                raise ValueError(f"{path.name}: placeholder {key} has no usable fact reference")
            for reference in references:
                if not isinstance(reference, str) or reference not in fact_ids:
                    raise ValueError(f"{path.name}: placeholder {key} references unknown fact {reference!r}")
    result: dict[str, tuple[str, bool, str, str]] = {}
    for key, item in mapping.items():
        if isinstance(item, dict):
            value = item.get("value")
            value_hinglish = item.get("value_hinglish", value)
            marked_mock = bool(item.get("mock", False))
            confidence = str(item.get("confidence", "high" if verified else "low")).casefold()
        else:
            value = item
            value_hinglish = value
            marked_mock = False
            confidence = "high" if verified else "low"
        if value is None or str(value).strip() == "":
            continue
        if verified and marked_mock:
            raise ValueError(f"{path.name}: verified fact {key} cannot be marked mock")
        if confidence not in {"high", "medium", "low"}:
            raise ValueError(f"{path.name}: fact {key} has invalid confidence {confidence!r}")
        localized = str(value_hinglish if value_hinglish is not None else value).strip()
        result[str(key)] = (str(value).strip(), marked_mock or not verified, confidence, localized)
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
    help_map_path: Path | None = None,
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

    help_map: dict = {}
    if help_map_path and help_map_path.exists():
        try:
            help_map = yaml.safe_load(help_map_path.read_text(encoding="utf-8-sig")) or {}
            if not isinstance(help_map, dict):
                raise ValueError("help_center_map.yaml must contain a mapping")
        except (OSError, ValueError, yaml.YAMLError) as exc:
            return [], [f"help_center_map.yaml: {exc}"], warnings

    help_fact_by_slug = {
        "internship-related": "HELP_INTERNSHIP_URL", "certificates": "HELP_CERTIFICATES_URL",
        "payment-related": "HELP_PAYMENT_URL", "skill": "HELP_SKILL_URL",
        "extension": "HELP_EXTENSION_URL", "placement-assistance": "HELP_PLACEMENT_URL",
        "offer-letter": "HELP_OFFER_LETTER_URL", "project": "HELP_PROJECT_URL",
        "internship-common-aptitude-test": "HELP_ICAT_URL", "curriculum": "HELP_CURRICULUM_URL",
        "internship-simulation": "HELP_SIMULATION_URL", "refund-program": "HELP_REFUND_URL",
        "referral": "HELP_REFERRAL_URL",
    }

    seen_ids: set[str] = set()
    seen_questions: list[tuple[str, str]] = []
    categories = Counter(row.category.value for row in rows)
    category_slugs = help_map.get("categories", {})
    entry_slugs = help_map.get("entries", {})
    if not isinstance(category_slugs, dict) or not isinstance(entry_slugs, dict):
        errors.append("help_center_map.yaml categories and entries must be mappings")
        category_slugs = {}
        entry_slugs = {}
    missing_categories = sorted({row.category.value for row in rows} - set(category_slugs))
    if missing_categories:
        errors.append("help_center_map.yaml missing category mapping(s): " + ", ".join(missing_categories))
    known_slugs = set(help_fact_by_slug)
    for category_name, mapped_slug in category_slugs.items():
        if mapped_slug not in known_slugs:
            errors.append(f"help_center_map.yaml: category {category_name!r} has unknown slug {mapped_slug!r}")
    for entry_id, mapped_slug in entry_slugs.items():
        if entry_id not in {row.id for row in rows}:
            errors.append(f"help_center_map.yaml: entry {entry_id!r} is not a KB entry")
        if mapped_slug not in known_slugs:
            errors.append(f"help_center_map.yaml: entry {entry_id!r} has unknown slug {mapped_slug!r}")
    default_slug = help_map.get("default")
    if default_slug is not None and default_slug not in known_slugs:
        errors.append(f"help_center_map.yaml: default has unknown slug {default_slug!r}")
    entries: list[BuiltEntry] = []

    for row in rows:
        prefix = row.id
        slug = entry_slugs.get(row.id, category_slugs.get(row.category.value, help_map.get("default")))
        help_fact_key = help_fact_by_slug.get(str(slug))
        row_verified = dict(verified)
        if help_fact_key and help_fact_key in verified:
            row_verified["HELP_LINK"] = verified[help_fact_key]
        elif "HELP_LINK" in PLACEHOLDER_RE.findall(row.answer):
            errors.append(f"{prefix}: no verified help-center URL mapped for section {slug!r}")
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
        confidence_keys: dict[str, str] = {}
        missing_keys: list[str] = []
        for key in keys:
            resolved = row_verified.get(key)
            if resolved is not None:
                value, is_mock, confidence, _value_hinglish = resolved
                if is_mock:
                    mock_keys.append(key)
                else:
                    verified_keys.append(key)
                    confidence_keys[key] = confidence
            else:
                fallback = mock.get(key)
                if fallback is None:
                    missing_keys.append(key)
                    continue
                value, _, _, _value_hinglish = fallback
                mock_keys.append(key)
            rendered = re.sub(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", value, rendered)
            if key in mock_keys and any(part in key.upper() for part in CLAIM_PLACEHOLDER_PARTS):
                warnings.append(
                    f"{prefix}: claim-type placeholder {key} uses MOCK data; verify before go-live"
                )

        if missing_keys:
            errors.append(f"{prefix}: missing fact key(s): {', '.join(missing_keys)}")
            continue
        low_confidence = any(value in {"medium", "low"} for value in confidence_keys.values())
        fee_keys = {"FEE_ICAT", "FEE_REGULAR", "FEE_CONFIRMATION"}
        other_uncertain = any(
            key not in fee_keys and value in {"medium", "low"}
            for key, value in confidence_keys.items()
        )
        if low_confidence and "FEE_CONFIRMATION" in keys:
            if other_uncertain:
                fee_confirmation = row_verified.get("FEE_CONFIRMATION", ("", False, "medium", ""))[0]
                rendered = rendered.replace(
                    fee_confirmation,
                    "Please confirm other details with the team; " + fee_confirmation,
                )
        elif low_confidence:
            if not re.search(r"connect (?:you with a human|a team member)|support team", rendered, re.IGNORECASE):
                rendered = rendered.rstrip()
                rendered += " Please confirm this on the official site or with the team."
        is_mock = bool(mock_keys)
        if is_mock:
            rendered = f"SAMPLE DATA — {rendered}"
        if len(rendered) > 500:
            errors.append(f"{prefix}: rendered answer is {len(rendered)} characters (maximum 500)")

        rendered_hinglish: str | None = None
        if not row.answer_hinglish or not row.answer_hinglish.strip():
            errors.append(f"{prefix}: Hinglish answer is required")
        else:
            if len(row.answer_hinglish) > 500:
                errors.append(f"{prefix}: Hinglish answer exceeds 500 characters")
            if is_mock and "SAMPLE DATA" not in row.answer_hinglish:
                errors.append(f"{prefix}: mock Hinglish answer must preserve SAMPLE DATA")
            literal_hinglish = _row_literal(row.answer_hinglish)
            for claim in CLAIM_WORDS:
                if re.search(rf"(?<!\w){re.escape(claim)}(?!\w)", literal_hinglish, re.IGNORECASE):
                    errors.append(f"{prefix}: Hinglish claim word {claim!r} must be supplied by a verified placeholder")
            missing_hinglish = sorted(set(PLACEHOLDER_RE.findall(row.answer_hinglish)) - set(keys))
            if missing_hinglish:
                errors.append(f"{prefix}: Hinglish answer has unsupported placeholder(s): {', '.join(missing_hinglish)}")
            hinglish_keys = set(PLACEHOLDER_RE.findall(row.answer_hinglish))
            if hinglish_keys != set(keys):
                errors.append(f"{prefix}: Hinglish answer must use the same placeholders as the English answer")
            rendered_hinglish = row.answer_hinglish
            for key in hinglish_keys:
                value = (row_verified.get(key) or mock.get(key))
                if value is not None:
                    rendered_hinglish = re.sub(
                        r"\{\{\s*" + re.escape(key) + r"\s*\}\}", value[3], rendered_hinglish
                    )
            if is_mock and "SAMPLE DATA" not in rendered_hinglish:
                rendered_hinglish = f"SAMPLE DATA — {rendered_hinglish}"
            if (
                low_confidence
                and "FEE_CONFIRMATION" not in hinglish_keys
                and not re.search(r"\b(confirm|connect|sampark|verify|jude|pushti)\b", rendered_hinglish, re.IGNORECASE)
            ):
                rendered_hinglish = rendered_hinglish.rstrip() + " Team se confirm karein."
            if len(rendered_hinglish) > 500:
                errors.append(f"{prefix}: rendered Hinglish answer is {len(rendered_hinglish)} characters (maximum 500)")
        for key, fallback in mock.items():
            for language, default_value, reply in (
                ("English", fallback[0], rendered),
                ("Hinglish", fallback[3], rendered_hinglish or ""),
            ):
                if default_value and default_value in reply:
                    errors.append(
                        f"{prefix}: mock default {key} appears in rendered {language} answer"
                    )
        entries.append(
            BuiltEntry(
                id=row.id,
                category=row.category,
                question=row.question,
                answer_template=row.answer,
                answer_rendered=rendered,
                answer_hinglish=rendered_hinglish,
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
                source_status=(
                    "pending" if is_mock else
                    "partly_verified" if (
                        low_confidence
                        or re.search(r"\b(?:don't have|cannot confirm|can't confirm|not confirmed|isn't confirmed|aren't confirmed|not stated)\b", rendered, re.IGNORECASE)
                        or re.search(r"(?:confirm nahi|confirm nahin|mere paas .* nahi|yahan .* nahi)", rendered_hinglish or "", re.IGNORECASE)
                    ) else
                    "verified"
                ),
                help_link=row_verified.get("HELP_LINK", ("", False, "", ""))[0],
            )
        )

    for category in Category:
        if category.value in {"payments_refunds", "certificates", "placement_support"}:
            continue
        count = categories.get(category.value, 0)
        if count < 4:
            warnings.append(f"{category.value}: only {count} KB entries (recommended minimum: 4)")

    return entries, errors, warnings
