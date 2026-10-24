from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import yaml

from src.kb.build import build_to_file
from src.kb.loader import load_csv, prepare_kb
from src.kb.report import render_report

REPO_ROOT = Path(__file__).resolve().parents[1]


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "kb", root / "kb")
    (root / "docs").mkdir()
    return root


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_loads_utf8_sig_and_hinglish_intact(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    path = root / "kb" / "knowledge_base.csv"
    original = path.read_bytes()
    path.write_bytes(b"\xef\xbb\xbf" + original.removeprefix(b"\xef\xbb\xbf"))

    rows, errors = load_csv(path)

    assert errors == []
    assert len(rows) == 33
    assert "paisa cut gaya access nahi mila" in rows[12].hinglish_variants


def test_verified_value_takes_precedence_and_clears_mock_flag(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    verified_path = root / "kb" / "verified_facts.yaml"
    verified_path.write_text(
        yaml.safe_dump(
            {"verified_facts": {"PROGRAM_TRACKS": "Verified test track"}},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = prepare_kb(root)

    assert not result.errors
    track = next(entry for entry in result.entries if entry.id == "CAT-002")
    assert "Verified test track" in track.answer_rendered
    assert track.facts_verified == ["PROGRAM_TRACKS"]
    assert track.facts_mock == []
    assert track.is_mock is False
    assert not track.answer_rendered.startswith("SAMPLE DATA")


def test_missing_placeholder_key_is_an_error_with_row_id(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    mock_path = root / "kb" / "mock_defaults.yaml"
    defaults = yaml.safe_load(mock_path.read_text(encoding="utf-8"))
    defaults.pop("PROGRAM_OVERVIEW")
    mock_path.write_text(yaml.safe_dump(defaults, sort_keys=False), encoding="utf-8")

    result = prepare_kb(root)

    assert any("CAT-001: missing fact key(s): PROGRAM_OVERVIEW" in error for error in result.errors)


def test_claim_lint_rejects_claim_in_literal_template(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    path = root / "kb" / "knowledge_base.csv"
    fields, rows = read_csv_rows(path)
    rows[0]["answer"] = "This program is guaranteed: {{PROGRAM_OVERVIEW}}."
    write_csv_rows(path, fields, rows)

    result = prepare_kb(root)

    assert any("CAT-001: claim word 'guaranteed'" in error for error in result.errors)


def test_rendered_answer_length_limit(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    mock_path = root / "kb" / "mock_defaults.yaml"
    defaults = yaml.safe_load(mock_path.read_text(encoding="utf-8"))
    defaults["PROGRAM_FEE"]["value"] = "[MOCK] " + ("x" * 520)
    mock_path.write_text(yaml.safe_dump(defaults, sort_keys=False), encoding="utf-8")

    result = prepare_kb(root)

    assert any("CAT-011: rendered answer is" in error for error in result.errors)


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    path = root / "kb" / "knowledge_base.csv"
    fields, rows = read_csv_rows(path)
    rows[1]["id"] = rows[0]["id"]
    write_csv_rows(path, fields, rows)

    result = prepare_kb(root)

    assert any("CAT-001: duplicate id" in error for error in result.errors)


def test_high_risk_entry_requires_handoff_offer(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    path = root / "kb" / "knowledge_base.csv"
    fields, rows = read_csv_rows(path)
    rows[10]["handoff_offer"] = "false"
    write_csv_rows(path, fields, rows)

    result = prepare_kb(root)

    assert any("CAT-011: high risk requires handoff_offer=true" in error for error in result.errors)


def test_build_is_deterministic(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    first = root / "first.json"
    second = root / "second.json"

    result1, payload1 = build_to_file(root, output_path=first)
    result2, payload2 = build_to_file(root, output_path=second)

    assert result1.errors == result2.errors == []
    assert payload1 is not None and payload2 is not None
    assert first.read_bytes() == second.read_bytes()
    assert len(payload1["entries"]) == 33


def test_report_counts_match_build_output(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    destination = root / "build.json"
    result, payload = build_to_file(root, output_path=destination)

    assert result.errors == []
    assert payload is not None
    report = render_report(payload)
    document = json.loads(destination.read_text(encoding="utf-8"))
    entries = document["entries"]
    assert len(entries) == 33
    assert "| program_info | 6 | 0 | 6 |" in report
    assert sum(entry["is_mock"] for entry in entries) == 33
    assert "PROGRAM_FEE" in report
