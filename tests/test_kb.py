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
    assert len(rows) == 69
    assert "paisa cut gaya access nahi mila" in rows[12].hinglish_variants


def test_verified_value_takes_precedence_and_clears_mock_flag(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    verified_path = root / "kb" / "verified_facts.yaml"
    verified_data = yaml.safe_load(verified_path.read_text(encoding="utf-8"))
    verified_data["verified_facts"]["placeholders"]["PROGRAM_TRACKS"] = {
        "value": "Verified test track", "fact": "F7", "confidence": "high"
    }
    verified_path.write_text(
        yaml.safe_dump(
            verified_data,
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = prepare_kb(root)

    assert not result.errors
    track = next(entry for entry in result.entries if entry.id == "CAT-002")
    assert "Verified test track" in track.answer_rendered
    assert set(track.facts_verified) == {"DOMAIN_LIST_NOTE", "PROGRAM_TRACKS"}
    assert track.facts_mock == []
    assert track.is_mock is False
    assert not track.answer_rendered.startswith("SAMPLE DATA")


def test_missing_placeholder_key_is_an_error_with_row_id(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    mock_path = root / "kb" / "mock_defaults.yaml"
    defaults = yaml.safe_load(mock_path.read_text(encoding="utf-8"))
    defaults.pop("PENDING_INFO")
    mock_path.write_text(yaml.safe_dump(defaults, sort_keys=False), encoding="utf-8")

    result = prepare_kb(root)

    assert any("CAT-003: missing fact key(s): PENDING_INFO" in error for error in result.errors)


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
    defaults["PENDING_INFO"]["value"] = "x" * 520
    mock_path.write_text(yaml.safe_dump(defaults, sort_keys=False), encoding="utf-8")

    result = prepare_kb(root)

    assert any("CAT-003: rendered answer is" in error for error in result.errors)


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
    assert len(payload1["entries"]) == 69


def test_report_counts_match_build_output(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    destination = root / "build.json"
    result, payload = build_to_file(root, output_path=destination)

    assert result.errors == []
    assert payload is not None
    report = render_report(payload)
    document = json.loads(destination.read_text(encoding="utf-8"))
    entries = document["entries"]
    assert len(entries) == 69
    assert "| program_info | 8 |" in report
    assert sum(entry["is_mock"] for entry in entries) == 31
    assert "PENDING_INFO" in report


def test_company_facts_are_sourced_and_mapped_without_unverified_answers() -> None:
    source = yaml.safe_load((REPO_ROOT / "kb" / "verified_facts.yaml").read_text(encoding="utf-8"))
    facts = source["verified_facts"]["facts"]
    assert {fact["id"] for fact in facts} == {f"F{index}" for index in range(1, 18)}
    assert all({"id", "text", "source", "retrieved", "confidence"} <= set(fact) for fact in facts)
    assert source["verified_facts"]["policies"][0]["id"] == "P1"
    result = prepare_kb(REPO_ROOT)
    assert result.errors == []
    assert len(result.entries) == 69
    pending = next(entry for entry in result.entries if entry.id == "CAT-003")
    assert pending.is_mock is True
    assert pending.answer_rendered.startswith("SAMPLE DATA —")
    assert pending.facts_mock == ["PENDING_INFO"]


def test_fact_entry_without_usable_id_fails_with_entry_name(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    verified_path = root / "kb" / "verified_facts.yaml"
    verified_data = yaml.safe_load(verified_path.read_text(encoding="utf-8"))
    verified_data["verified_facts"]["facts"][0]["id"] = "  "
    verified_path.write_text(
        yaml.safe_dump(verified_data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    result = prepare_kb(root)

    assert any(
        "fact entry #1 has missing or unusable id" in error
        for error in result.errors
    )


def test_every_entry_requires_a_hinglish_answer(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    path = root / "kb" / "knowledge_base.csv"
    fields, rows = read_csv_rows(path)
    rows[0]["answer_hinglish"] = ""
    write_csv_rows(path, fields, rows)

    result = prepare_kb(root)

    assert any("CAT-001: Hinglish answer is required" in error for error in result.errors)


def test_customer_answers_hide_internal_sources_and_localize_fee_suffix() -> None:
    result = prepare_kb(REPO_ROOT)
    assert result.errors == []
    internal_terms = ("sources", "knowledge base", "fact id", "internal")
    for entry in result.entries:
        for answer in (entry.answer_rendered, entry.answer_hinglish or ""):
            assert not any(term in answer.casefold() for term in internal_terms), entry.id
    fee = next(entry for entry in result.entries if entry.id == "CAT-041")
    assert fee.answer_hinglish.rstrip(". ").endswith("fees badal sakti hain; payment se pehle official site par confirm kar lein")
    assert "fees can change" not in fee.answer_hinglish.casefold()


def test_medium_low_facts_get_confirmation_and_fees_end_with_required_note() -> None:
    result = prepare_kb(REPO_ROOT)
    assert result.errors == []
    entries = {entry.id: entry for entry in result.entries}
    assert "confirm" in entries["CAT-002"].answer_rendered.casefold()
    assert "confirm" in entries["CAT-066"].answer_rendered.casefold()
    required = "fees can change, please confirm on the official site before paying"
    for entry_id in ("CAT-011", "CAT-041", "CAT-026"):
        assert entries[entry_id].answer_rendered.rstrip(". ").endswith(required)


def test_iso_claims_must_be_backed_by_a_verified_placeholder(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    path = root / "kb" / "knowledge_base.csv"
    fields, rows = read_csv_rows(path)
    rows[18]["answer"] = "The certificate is ISO verified. {{CERTIFICATE_STATUS}}."
    write_csv_rows(path, fields, rows)
    result = prepare_kb(root)
    assert any("CAT-019: claim word 'ISO'" in error for error in result.errors)
