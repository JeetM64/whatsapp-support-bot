from __future__ import annotations

from pathlib import Path

from src.rag.eval import load_cases


def test_retrieval_eval_has_balanced_company_cases_and_required_out_of_kb() -> None:
    root = Path(__file__).resolve().parents[1]
    cases = load_cases(root / "eval" / "retrieval_cases.csv")
    assert len(cases) >= 90
    assert len(cases) == 140
    assert sum(case["split"] == "dev" for case in cases) == 70
    assert sum(case["split"] == "test" for case in cases) == 70
    assert sum(case["type"] == "out_of_kb" for case in cases) >= 20
    assert sum(case["type"] == "prompt_injection" for case in cases) >= 10
