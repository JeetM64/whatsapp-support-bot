from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from .models import BuiltEntry, KBRow
from .validate import validate_and_render

CSV_FIELDS = (
    "id",
    "category",
    "question",
    "answer",
    "answer_hinglish",
    "hinglish_variants",
    "keywords",
    "risk_level",
    "handoff_offer",
    "escalate_if_unmatched",
    "owner",
    "last_reviewed",
)


@dataclass
class PrepareResult:
    entries: list[BuiltEntry]
    errors: list[str]
    warnings: list[str]


def load_csv(path: Path) -> tuple[list[KBRow], list[str]]:
    rows: list[KBRow] = []
    errors: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                return [], ["knowledge_base.csv: missing header row"]
            missing = [field for field in CSV_FIELDS if field not in reader.fieldnames]
            extra = [field for field in reader.fieldnames if field not in CSV_FIELDS]
            if missing or extra:
                details = []
                if missing:
                    details.append(f"missing columns: {', '.join(missing)}")
                if extra:
                    details.append(f"unexpected columns: {', '.join(extra)}")
                return [], ["knowledge_base.csv: " + "; ".join(details)]

            for line_number, raw in enumerate(reader, start=2):
                row_id = (raw.get("id") or "").strip() or f"<row {line_number}>"
                try:
                    rows.append(KBRow.model_validate(raw))
                except ValidationError as exc:
                    for issue in exc.errors():
                        field = ".".join(str(part) for part in issue["loc"])
                        errors.append(f"{row_id}: {field}: {issue['msg']}")
    except OSError as exc:
        errors.append(f"knowledge_base.csv: {exc}")
    return rows, errors


def prepare_kb(
    root: Path,
    *,
    csv_path: Path | None = None,
    verified_path: Path | None = None,
    mock_path: Path | None = None,
    today: date | None = None,
) -> PrepareResult:
    kb_dir = root / "kb"
    rows, errors = load_csv(csv_path or kb_dir / "knowledge_base.csv")
    if errors:
        return PrepareResult([], errors, [])
    entries, validation_errors, warnings = validate_and_render(
        rows,
        verified_path or kb_dir / "verified_facts.yaml",
        mock_path or kb_dir / "mock_defaults.yaml",
        help_map_path=kb_dir / "help_center_map.yaml",
        today=today,
    )
    return PrepareResult(entries, validation_errors, warnings)
