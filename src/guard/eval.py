from __future__ import annotations
import csv
from pathlib import Path
from src.guard import GuardRules

def evaluate(root: Path) -> str:
    rules=GuardRules(root)
    rows=list(csv.DictReader((root/"eval/escalation_cases.csv").open(encoding="utf-8-sig",newline="")))
    result=[]
    for row in rows:
        ctx=row["context"]
        got=rules.classify(row["query"],frustration_loop=ctx=="loop",unmatched_high_risk=ctx=="unmatched",status_authorized=ctx!="unverified")
        # An offer_human result meets a must-escalate routing expectation while
        # remaining ticket-free until the customer accepts that offer.
        escalated=got.action in {"escalate","support","kb_first_aid_ticket","offer_human"}
        result.append((row,escalated,got.action,got.reason_code))
    lines=["| Split | Must escalate | Correct escalations | Recall | Must answer | False escalations | False escalate rate |","|---|---:|---:|---:|---:|---:|---:|"]
    for split in ("dev","test"):
        data=[r for r in result if r[0]["split"]==split]
        pos=[r for r in data if r[0]["expected"]=="must_escalate"]
        neg=[r for r in data if r[0]["expected"]=="must_answer"]
        tp=sum(r[1] for r in pos); fp=sum(r[1] for r in neg)
        lines.append(f"| {split} | {len(pos)} | {tp} | {tp/max(len(pos),1):.1%} | {len(neg)} | {fp} | {fp/max(len(neg),1):.1%} |")
    lines.extend(["","| Case | Split | Expected | Got | Rule |","|---|---|---|---|---|"])
    for row,escalated,action,reason in result:
        if (row["expected"]=="must_escalate") != escalated:
            lines.append(f"| {row['case_id']} | {row['split']} | {row['expected']} | {action} ({reason}) | {row['rule']} |")
    return "\n".join(lines)
if __name__=="__main__":
    root=Path.cwd().resolve()
    print(evaluate(root))
