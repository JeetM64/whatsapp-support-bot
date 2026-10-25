from pathlib import Path
import yaml
from src.guard.l1 import merge_l1

def test_multiturn_eval_has_required_scenarios():
    root=Path(__file__).parents[1]
    data=yaml.safe_load((root/"eval/multiturn_cases.yaml").read_text(encoding="utf-8"))
    assert len(data["scenarios"]) >= 12
    kinds={item["type"] for item in data["scenarios"]}
    assert {"follow-up","option-choice","loop-to-escalate","post-handoff","dedupe","out-of-hours","identity-mismatch","sensitive-data"} <= kinds

def test_l1_merge_truth_table_cannot_cancel_l0():
    cases=[
        (False,{"needs_human":False,"confidence":1.0},False),
        (False,{"needs_human":True,"confidence":0.79},False),
        (False,{"needs_human":True,"confidence":0.8},True),
        (True,{"needs_human":False,"confidence":0.0},True),
        (True,{"needs_human":True,"confidence":1.0},True),
    ]
    for l0,l1,expected in cases:
        assert merge_l1(l0,l1) is expected
