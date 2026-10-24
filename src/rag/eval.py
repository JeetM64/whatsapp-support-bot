from __future__ import annotations

import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import RagConfig
from .decision import decide
from .models import Decision
from .retriever import RetrievalOutput, Retriever


@dataclass
class CaseResult:
    case: dict[str, str]
    retrieval: RetrievalOutput
    got_decision: str
    reason_code: str
    got_ids: list[str]


def load_cases(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "id", "split", "type", "query", "expected_ids", "expected_decision"
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("retrieval_cases.csv has missing required columns")
        cases = list(reader)
    if len(cases) < 90:
        raise ValueError(f"retrieval evaluation requires at least 90 cases; found {len(cases)}")
    splits = {split: sum(case["split"] == split for case in cases) for split in {"dev", "test"}}
    if splits != {"dev": len(cases) // 2, "test": len(cases) - len(cases) // 2}:
        raise ValueError(f"expected a 50/50 dev/test split; got {splits}")
    return cases


def _expected_ids(case: dict[str, str]) -> set[str]:
    raw = case["expected_ids"].strip()
    return set() if raw.upper() == "NONE" else {value.strip() for value in raw.split("|") if value.strip()}


def _expected_decision(case: dict[str, str]) -> str:
    return case["expected_decision"].strip().upper()


def _retrieve_cases(
    cases: list[dict[str, str]], retriever: Retriever
) -> list[tuple[dict[str, str], RetrievalOutput]]:
    return [(case, retriever.retrieve(case["query"])) for case in cases]


def _tune(
    dev_rows: list[tuple[dict[str, str], RetrievalOutput]],
    retriever: Retriever,
    config: RagConfig,
) -> dict[str, float]:
    evaluation = config.evaluation
    seed = int(evaluation.get("seed", 0))
    grids = [
        [float(value) for value in evaluation["answer_threshold_grid"]],
        [float(value) for value in evaluation["high_risk_threshold_grid"]],
        [float(value) for value in evaluation["margin_threshold_grid"]],
        [float(value) for value in evaluation["low_threshold_grid"]],
        [float(value) for value in evaluation["ambiguity_margin_grid"]],
    ]
    combinations = [
        (answer, high, margin, low, ambiguity)
        for answer in grids[0]
        for high in grids[1]
        for margin in grids[2]
        for low in grids[3]
        for ambiguity in grids[4]
        if high >= answer + 0.08 and low < answer
    ]
    random.Random(seed).shuffle(combinations)
    best: tuple[tuple[float, ...], dict[str, float]] | None = None
    for answer, high, margin, low, ambiguity in combinations:
        config.thresholds["answer"] = answer
        config.thresholds["answer_high"] = high
        config.thresholds["margin"] = margin
        config.thresholds["low"] = low
        config.decision["ambiguity_margin"] = ambiguity
        correct = 0
        false_accepts = 0
        injection_errors = 0
        for case, retrieval in dev_rows:
            result = decide(case["query"], retrieval, retriever.entries, config)
            expected = _expected_decision(case)
            correct += result.decision.value == expected
            if case["type"] == "out_of_kb" and result.decision == Decision.ANSWER:
                false_accepts += 1
            if case["type"] == "prompt_injection" and result.decision != Decision.NO_MATCH:
                injection_errors += 1
        if false_accepts or injection_errors:
            continue
        accuracy = correct / max(len(dev_rows), 1)
        score = (accuracy, -answer, -high, -margin, -low, -ambiguity)
        chosen = {
            "answer": answer,
            "answer_high": high,
            "margin": margin,
            "low": low,
            "ambiguity_margin": ambiguity,
        }
        if best is None or score > best[0]:
            best = (score, chosen)
    return best[1] if best else dict(config.thresholds)


def _persist_thresholds(root: Path, thresholds: dict[str, float]) -> None:
    path = root / "config" / "rag.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    data["thresholds"].update(thresholds)
    data["decision"]["ambiguity_margin"] = thresholds["ambiguity_margin"]
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )


def _metrics(rows: list[CaseResult]) -> dict[str, Any]:
    in_kb = [row for row in rows if _expected_ids(row.case)]
    out_kb = [row for row in rows if not _expected_ids(row.case)]
    top1 = sum(
        bool(row.got_ids) and row.got_ids[0] in _expected_ids(row.case)
        for row in in_kb
    ) / max(len(in_kb), 1)
    top3 = sum(
        bool(set(row.got_ids[:3]) & _expected_ids(row.case))
        for row in in_kb
    ) / max(len(in_kb), 1)
    decision_accuracy = sum(
        row.got_decision == _expected_decision(row.case) for row in rows
    ) / max(len(rows), 1)
    false_accept_rate = sum(
        row.got_decision == Decision.ANSWER.value for row in out_kb
    ) / max(len(out_kb), 1)
    injection = [row for row in rows if row.case["type"] == "prompt_injection"]
    injection_pass = sum(
        row.got_decision == Decision.NO_MATCH.value for row in injection
    ) / max(len(injection), 1)
    return {
        "count": len(rows),
        "in_kb_count": len(in_kb),
        "out_kb_count": len(out_kb),
        "top1": top1,
        "top3": top3,
        "decision_accuracy": decision_accuracy,
        "false_accept_rate": false_accept_rate,
        "injection_pass": injection_pass,
    }


def _render_report(
    dev_results: list[CaseResult],
    test_results: list[CaseResult],
    metrics: dict[str, Any],
    thresholds: dict[str, float],
    seed: int,
) -> str:
    all_results = [("dev", dev_results), ("test", test_results)]
    lines = [
        "# Retrieval evaluation",
        "",
        "Thresholds were selected using the dev split only. Metrics below use the held-out test split.",
        f"Split seed: {seed}; test cases: {metrics['count']}.",
        "",
        "## Test metrics",
        "",
        "| Metric | Result | Target | Status |",
        "|---|---:|---:|---|",
        f"| In-KB top-1 accuracy | {metrics['top1']:.1%} | report | INFO |",
        f"| In-KB top-3 accuracy | {metrics['top3']:.1%} | >=95% | {'PASS' if metrics['top3'] >= 0.95 else 'FAIL'} |",
        f"| Decision accuracy | {metrics['decision_accuracy']:.1%} | report | INFO |",
        f"| Out-of-KB false-accept rate (ANSWER decisions) | {metrics['false_accept_rate']:.1%} | 0% | {'PASS' if metrics['false_accept_rate'] == 0 else 'FAIL'} |",
        f"| Prompt-injection handled | {metrics['injection_pass']:.1%} | 100% | {'PASS' if metrics['injection_pass'] == 1 else 'FAIL'} |",
        "",
        "## Thresholds selected on dev",
        "",
        f"- Answer: {thresholds['answer']:.2f}",
        f"- High-risk answer: {thresholds['answer_high']:.2f}",
        f"- Margin: {thresholds['margin']:.2f}",
        f"- Low: {thresholds['low']:.2f}",
        f"- Ambiguity margin: {thresholds['ambiguity_margin']:.2f}",
        "",
        "## Decision accuracy per type",
        "",
        "| Split | Type | Count | Decision accuracy |",
        "|---|---|---:|---:|",
    ]
    for split, rows in all_results:
        types: dict[str, list[CaseResult]] = defaultdict(list)
        for result in rows:
            types[result.case["type"]].append(result)
        for case_type in sorted(types):
            subset = types[case_type]
            accuracy = sum(
                row.got_decision == _expected_decision(row.case) for row in subset
            ) / max(len(subset), 1)
            lines.append(f"| {split} | {case_type} | {len(subset)} | {accuracy:.1%} |")
    failures: list[tuple[str, CaseResult, str]] = []
    for split, rows in all_results:
        for row in rows:
            if row.got_decision == _expected_decision(row.case):
                continue
            if row.case["expected_decision"].strip().upper() == "ANSWER":
                category = "over-cautious" if (
                    not _expected_ids(row.case)
                    or set(row.got_ids[:3]) & _expected_ids(row.case)
                ) else "wrong entry"
            elif _expected_ids(row.case) and not (set(row.got_ids[:3]) & _expected_ids(row.case)):
                category = "wrong entry"
            elif (
                row.case["expected_decision"].strip().upper() == "CLARIFY"
                and row.got_decision == "NO_MATCH"
            ):
                category = "missed clarification"
            elif (
                row.case["expected_decision"].strip().upper() == "NO_MATCH"
                and row.got_decision == "CLARIFY"
            ):
                category = "missed out-of-scope/injection block"
            else:
                category = "CSV expectation review"
            failures.append((split, row, category))
    counts = {name: sum(category == name for _, _, category in failures) for name in (
        "over-cautious", "wrong entry", "missed clarification",
        "missed out-of-scope/injection block", "CSV expectation review"
    )}
    lines.extend([
        "",
        "## Failure classification",
        "",
        f"Over-cautious: {counts['over-cautious']}; wrong entry: {counts['wrong entry']}; "
        f"missed clarification: {counts['missed clarification']}; missed out-of-scope/injection "
        f"block: {counts['missed out-of-scope/injection block']}; wrong CSV expectation: "
        f"{counts['CSV expectation review']}.",
        "",
        "## Failures on both splits",
        "",
    ])
    if not failures:
        lines.append("None.")
    else:
        for split, row, category in failures:
            lines.append(
                f"- [{split}] {row.case['id']} ({row.case['type']}, {category}): "
                f"“{row.case['query']}” — expected {_expected_decision(row.case)}; "
                f"got {row.got_decision}; confidence={row.retrieval.confidence:.3f}; "
                f"margin={row.retrieval.margin:.3f}; reason={row.reason_code}; "
                f"top3={','.join(row.got_ids[:3]) or 'NONE'}."
            )
    lines.append("")
    return "\n".join(lines)


def run_eval(root: Path, retriever: Retriever, config: RagConfig) -> tuple[str, dict[str, Any]]:
    cases = load_cases(root / "eval" / "retrieval_cases.csv")
    dev_cases = [case for case in cases if case["split"] == "dev"]
    test_cases = [case for case in cases if case["split"] == "test"]

    dev_retrieval = _retrieve_cases(dev_cases, retriever)
    tuned = _tune(dev_retrieval, retriever, config)
    config.thresholds.update(tuned)
    _persist_thresholds(root, tuned)

    def decisions_for(rows: list[tuple[dict[str, str], RetrievalOutput]]) -> list[CaseResult]:
        results: list[CaseResult] = []
        for case, retrieval in rows:
            decision = decide(case["query"], retrieval, retriever.entries, config)
            results.append(CaseResult(
                case=case,
                retrieval=retrieval,
                got_decision=decision.decision.value,
                reason_code=decision.reason_code,
                got_ids=[candidate.id for candidate in retrieval.candidates],
            ))
        return results

    dev_results = decisions_for(dev_retrieval)
    test_rows: list[CaseResult] = []
    for case, retrieval in _retrieve_cases(test_cases, retriever):
        decision = decide(case["query"], retrieval, retriever.entries, config)
        test_rows.append(
            CaseResult(
                case=case,
                retrieval=retrieval,
                got_decision=decision.decision.value,
                reason_code=decision.reason_code,
                got_ids=[candidate.id for candidate in retrieval.candidates],
            )
        )
    metrics = _metrics(test_rows)
    report = _render_report(
        dev_results,
        test_rows,
        metrics,
        tuned,
        int(config.evaluation.get("seed", 0)),
    )
    (root / "docs" / "rag_eval.md").write_text(report, encoding="utf-8", newline="\n")
    return report, metrics
