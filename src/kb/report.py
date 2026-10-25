from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .loader import PrepareResult, prepare_kb
from .models import Category

LEGACY_CATEGORIES = {"payments_refunds", "certificates", "placement_support"}


def render_report(payload: dict[str, Any]) -> str:
    entries = payload["entries"]
    totals: Counter[str] = Counter(entry["category"] for entry in entries)
    verified: Counter[str] = Counter(
        entry["category"] for entry in entries if not entry["is_mock"]
    )
    mock: Counter[str] = Counter(
        entry["category"] for entry in entries if entry["is_mock"]
    )
    lines = [
        "# KB go-live report",
        "",
        "**SAMPLE DATA:** every answer using a mock fact is labeled in the generated KB.",
        "",
        "| Category | Total | Verified | Mock |",
        "|---|---:|---:|---:|",
    ]
    for category in Category:
        name = category.value
        if name in LEGACY_CATEGORIES:
            continue
        lines.append(f"| {name} | {totals[name]} | {verified[name]} | {mock[name]} |")
    lines.extend(["", "## Entries using mock facts", ""])
    mocked_entries = [entry for entry in entries if entry["facts_mock"]]
    if not mocked_entries:
        lines.append("None.")
    else:
        for entry in mocked_entries:
            keys = ", ".join(entry["facts_mock"])
            lines.append(f"- {entry['id']} — {keys}")

    required = sorted({key for entry in entries for key in entry["facts_required"]})
    verified_keys = {key for entry in entries for key in entry["facts_verified"]}
    missing = [key for key in required if key not in verified_keys]
    lines.extend(["", "## Missing from verified_facts.yaml", ""])
    if missing:
        lines.extend(f"- {key}" for key in missing)
    else:
        lines.append("None.")
    lines.extend(
        [
            "",
            f"Generated entries: {len(entries)}",
            f"Content hash: {payload['content_hash']}",
            "",
        ]
    )
    return "\n".join(lines)


def create_report(root: Path) -> tuple[PrepareResult, str | None]:
    result = prepare_kb(root)
    if result.errors:
        return result, None
    from .build import payload_for

    report = render_report(payload_for(result.entries))
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "kb_report.md").write_text(report, encoding="utf-8", newline="\n")
    return result, report
