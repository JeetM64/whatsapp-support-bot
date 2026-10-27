"""Evaluate English/Hinglish decision and top-entry parity by split."""
from __future__ import annotations

import csv
from pathlib import Path

from .config import RagConfig
from .decision import decide
from .retriever import Retriever


def evaluate(root: Path) -> str:
    with (root / "eval" / "paired_cases.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    retriever = Retriever(root, RagConfig.load(root))
    results: dict[str, list[tuple[dict[str, str], str, str, str, str]]] = {"dev": [], "test": []}
    for row in rows:
        pair = []
        for query in (row["english"], row["hinglish"]):
            retrieval = retriever.retrieve(query)
            decision = decide(query, retrieval, retriever.entries, retriever.config)
            pair.append((decision.decision.value, retrieval.candidates[0].id if retrieval.candidates else "NONE"))
        results[row["split"]].append((row, pair[0][0], pair[0][1], pair[1][0], pair[1][1]))
    lines = ["| Split | Pairs | Decision divergence | Top-entry divergence |", "|---|---:|---:|---:|"]
    for split, data in results.items():
        lines.append(f"| {split} | {len(data)} | {sum(a!=c for _,a,_,c,_ in data)}/{len(data)} ({sum(a!=c for _,a,_,c,_ in data)/max(len(data),1):.1%}) | {sum(b!=d for _,_,b,_,d in data)}/{len(data)} ({sum(b!=d for _,_,b,_,d in data)/max(len(data),1):.1%}) |")
    lines.extend(["", "| Pair | Split | EN decision/id | HI decision/id |", "|---|---|---|---|"])
    for split, data in results.items():
        for row, a, b, c, d in data:
            if a != c or b != d:
                lines.append(f"| {row['pair_id']} | {split} | {a}/{b} | {c}/{d} |")
    report = "\n".join(lines)
    (root / "docs" / "paired_eval.md").write_text(report, encoding="utf-8")
    return report


if __name__ == "__main__":
    print(evaluate(Path.cwd().resolve()))
