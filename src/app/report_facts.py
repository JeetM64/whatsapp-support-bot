from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


def generate(root: Path) -> Path:
    data = json.loads((root / "kb" / "build" / "knowledge_base.json").read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    categories = Counter(e.get("category", "unknown") for e in entries)
    risks = Counter(e.get("risk_level", "unknown") for e in entries)
    sources = Counter(e.get("source_status", "unknown") for e in entries)
    handoff = sum(bool(e.get("handoff_offer")) for e in entries)
    unknowns = []
    for e in entries:
        text = e.get("answer_rendered", "")
        if "don't have" in text.casefold() or "not confirmed" in text.casefold() or "unconfirmed" in text.casefold():
            unknowns.append(f"- {e.get('id')}: {e.get('question')} — {text}")
    rag_report = (root / "docs" / "rag_eval.md").read_text(encoding="utf-8") if (root / "docs" / "rag_eval.md").exists() else "Not run."
    escalation = (root / "docs" / "eval_summary.md").read_text(encoding="utf-8") if (root / "docs" / "eval_summary.md").exists() else "Not run."
    lines = ["# Generated report facts", "", f"Generated from current build and docs; content hash: `{data.get('content_hash','unknown')}`.", "", f"## Knowledge base ({len(entries)} entries)", "", "### Category counts", ""]
    lines += [f"- {k}: {v}" for k, v in sorted(categories.items())]
    lines += ["", "### Risk counts", ""] + [f"- {k}: {v}" for k, v in sorted(risks.items())]
    lines += ["", "### Source status counts", ""] + [f"- {k}: {v}" for k, v in sorted(sources.items())]
    lines += ["", f"Handoff offers: {handoff}", "", "## Escalation and SLA", "", "Rules: explicit human request, money loss/payment trouble, refund disputes, trust/approval, threats/abuse, sensitive data, repeated failures and high-risk unmatched questions are handled by configured guardrails. See `config/escalation_rules.yaml`.", "", "Business hours and priority deadlines are loaded from runtime configuration. This report does not infer a deadline when configuration is absent.", "", "## Evaluation", "", rag_report, "", escalation, "", "## Runtime measurements", "", "- Tests: latest recorded full suite: 191 passed; rerun `python -m pytest -q` to refresh.", "- Latency, cold start and RAM: not measured in this run.", "- Cost per 1,000 messages: $0 in no-LLM mode; no provider token logs are generated.", "", "## Unconfirmed details", "", *(unknowns or ["- None detected in rendered answer text."]), "", "## Assumptions and limitations", "", "- KB content is assignment sample data and requires team confirmation.", "- Test split has limited sample size and is partially seen; evaluation results are not a production guarantee.", "- No live WhatsApp delivery, external hosting or real browser/mobile visual check is claimed.", ""]
    target = root / "deliverables" / "REPORT_FACTS.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
