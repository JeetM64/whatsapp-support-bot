from __future__ import annotations

import csv
import json
import re
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
    verified_data["verified_facts"]["placeholders"]["PROGRAM_OVERVIEW"] = {
        "value": "Verified test track", "fact": "F5", "confidence": "high"
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
    track = next(entry for entry in result.entries if entry.id == "CAT-001")
    assert "Verified test track" in track.answer_rendered
    assert {"HELP_LINK", "PROGRAM_DELIVERABLES", "PROGRAM_OVERVIEW"} <= set(track.facts_verified)
    assert track.facts_mock == []
    assert track.is_mock is False
    assert not track.answer_rendered.startswith("SAMPLE DATA")


def test_missing_placeholder_key_is_an_error_with_row_id(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    verified_path = root / "kb" / "verified_facts.yaml"
    verified_data = yaml.safe_load(verified_path.read_text(encoding="utf-8"))
    verified_data["verified_facts"]["placeholders"].pop("PROGRAM_OVERVIEW")
    verified_path.write_text(yaml.safe_dump(verified_data, sort_keys=False), encoding="utf-8")

    result = prepare_kb(root)

    assert any("CAT-003: missing fact key(s): PROGRAM_OVERVIEW" in error for error in result.errors)


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
    verified_path = root / "kb" / "verified_facts.yaml"
    verified_data = yaml.safe_load(verified_path.read_text(encoding="utf-8"))
    verified_data["verified_facts"]["placeholders"]["PROGRAM_OVERVIEW"]["value"] = "x" * 520
    verified_path.write_text(yaml.safe_dump(verified_data, sort_keys=False), encoding="utf-8")

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
    baseline = prepare_kb(root)
    high_risk = next(entry for entry in baseline.entries if entry.risk_level.value == "high")
    fields, rows = read_csv_rows(path)
    target = next(row for row in rows if row["id"] == high_risk.id)
    target["handoff_offer"] = "false"
    write_csv_rows(path, fields, rows)

    result = prepare_kb(root)

    assert any(f"{high_risk.id}: high risk requires handoff_offer=true" in error for error in result.errors)


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
    for category in {entry["category"] for entry in entries}:
        selected = [entry for entry in entries if entry["category"] == category]
        line = f"| {category} | {len(selected)} | {sum(not entry['is_mock'] for entry in selected)} | {sum(entry['is_mock'] for entry in selected)} |"
        assert line in report
    for entry in entries:
        if entry["facts_mock"]:
            assert f"- {entry['id']} — {', '.join(entry['facts_mock'])}" in report


def test_company_facts_are_sourced_and_mapped_without_unverified_answers() -> None:
    source = yaml.safe_load((REPO_ROOT / "kb" / "verified_facts.yaml").read_text(encoding="utf-8"))
    facts = source["verified_facts"]["facts"]
    assert {fact["id"] for fact in facts} == {f"F{index}" for index in range(1, 19)}
    assert all({"id", "text", "source", "retrieved", "confidence"} <= set(fact) for fact in facts)
    assert source["verified_facts"]["policies"][0]["id"] == "P1"
    result = prepare_kb(REPO_ROOT)
    assert result.errors == []
    assert len(result.entries) == 69
    rewritten = next(entry for entry in result.entries if entry.id == "CAT-003")
    assert rewritten.is_mock is False
    assert rewritten.source_status == "partly_verified"
    assert "SAMPLE DATA" not in rewritten.answer_rendered
    assert rewritten.facts_mock == []
    assert all(entry.help_link.startswith("https://internshipstudio.tawk.help/category/") for entry in result.entries)


def test_mock_default_fallback_keeps_sample_label(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    path = root / "kb" / "knowledge_base.csv"
    fields, rows = read_csv_rows(path)
    target = next(row for row in rows if row["id"] == "CAT-001")
    target["answer"] = "{{PENDING_INFO}}"
    target["answer_hinglish"] = "SAMPLE DATA — {{PENDING_INFO}}"
    write_csv_rows(path, fields, rows)

    result = prepare_kb(root)

    assert any(
        "CAT-001: mock default PENDING_INFO appears in rendered English answer" in error
        for error in result.errors
    )
    mock_entry = next(entry for entry in result.entries if entry.id == "CAT-001")
    assert mock_entry.is_mock is True
    assert mock_entry.source_status == "pending"
    assert mock_entry.answer_rendered.startswith("SAMPLE DATA —")
    assert mock_entry.facts_mock == ["PENDING_INFO"]


def test_literal_mock_default_value_fails_build_with_entry_and_key(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    defaults = yaml.safe_load((root / "kb" / "mock_defaults.yaml").read_text(encoding="utf-8"))
    path = root / "kb" / "knowledge_base.csv"
    fields, rows = read_csv_rows(path)
    target = next(row for row in rows if row["id"] == "CAT-001")
    target["answer"] = "iStudio: " + defaults["PENDING_INFO"]["value"]
    target["answer_hinglish"] = "iStudio: " + defaults["PENDING_INFO"]["value_hinglish"]
    write_csv_rows(path, fields, rows)

    result = prepare_kb(root)

    assert any(
        "CAT-001: mock default PENDING_INFO appears in rendered English answer" in error
        for error in result.errors
    )


def test_help_center_links_use_the_verified_index_fact_for_every_entry() -> None:
    source = yaml.safe_load((REPO_ROOT / "kb" / "verified_facts.yaml").read_text(encoding="utf-8"))
    fact = next(item for item in source["verified_facts"]["facts"] if item["id"] == "F18")
    assert fact["source"] == "help center index"
    assert fact["confidence"] == "high"
    result = prepare_kb(REPO_ROOT)
    assert result.errors == []
    assert len({entry.help_link for entry in result.entries}) > 1


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


def test_customer_answers_hide_internal_sources_and_localize_fee_caveat() -> None:
    result = prepare_kb(REPO_ROOT)
    assert result.errors == []
    internal_terms = ("sources", "knowledge base", "fact id", "internal")
    for entry in result.entries:
        for answer in (entry.answer_rendered, entry.answer_hinglish or ""):
            assert not any(term in answer.casefold() for term in internal_terms), entry.id
            assert not any(term in answer.casefold() for term in ("sample data", "pending info", "not verified yet")), entry.id
    fee = next(entry for entry in result.entries if entry.id == "CAT-041")
    assert "Fees badal sakti hain, isliye payment se pehle official site par confirm kar lein" in fee.answer_hinglish
    assert "fees can change" not in fee.answer_hinglish.casefold()


def test_every_answer_uses_voice_glossary_and_has_a_next_step() -> None:
    result = prepare_kb(REPO_ROOT)
    glossary = yaml.safe_load((REPO_ROOT / "kb" / "glossary.yaml").read_text(encoding="utf-8"))
    terms = [term.casefold() for term in glossary["terms"]]
    action = re.compile(r"https?://|would you like|connect you|contact |email |call |kya main|dekhein|par likhein|par call karein", re.IGNORECASE)
    for entry in result.entries:
        for language, answer in (("English", entry.answer_rendered), ("Hinglish", entry.answer_hinglish or "")):
            assert any(term in answer.casefold() for term in terms), f"{entry.id} {language}: missing glossary term"
            assert action.search(answer), f"{entry.id} {language}: missing actionable next step"


def test_answer_fact_tokens_have_english_hinglish_parity() -> None:
    result = prepare_kb(REPO_ROOT)
    assert result.errors == []
    number_re = re.compile(r"\d+")
    email_re = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    url_re = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)

    def facts(text: str) -> set[str]:
        tokens = number_re.findall(text)
        tokens += [value.casefold() for value in email_re.findall(text)]
        tokens += [value.rstrip(".,;:!?]").casefold() for value in url_re.findall(text)]
        return set(tokens)

    for entry in result.entries:
        en = facts(entry.answer_rendered)
        hi = facts(entry.answer_hinglish or "")
        assert en <= hi, f"{entry.id}: English facts missing from Hinglish: {sorted(en-hi)}"
        assert hi <= en, f"{entry.id}: Hinglish facts missing from English: {sorted(hi-en)}"


def test_medium_low_facts_get_confirmation_and_fees_include_required_note() -> None:
    result = prepare_kb(REPO_ROOT)
    assert result.errors == []
    entries = {entry.id: entry for entry in result.entries}
    assert "confirm" in entries["CAT-002"].answer_rendered.casefold()
    assert "confirm" in entries["CAT-066"].answer_rendered.casefold()
    required = "fees can change, so please confirm on the official site before paying"
    for entry_id in ("CAT-011", "CAT-041"):
        assert required in entries[entry_id].answer_rendered.casefold()


def test_iso_claims_must_be_backed_by_a_verified_placeholder(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    path = root / "kb" / "knowledge_base.csv"
    fields, rows = read_csv_rows(path)
    rows[18]["answer"] = "The certificate is ISO verified. {{CERTIFICATE_STATUS}}."
    write_csv_rows(path, fields, rows)
    result = prepare_kb(root)
    assert any("CAT-019: claim word 'ISO'" in error for error in result.errors)
