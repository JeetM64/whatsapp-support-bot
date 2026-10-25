from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

@dataclass(frozen=True)
class GuardResult:
    reason_code: str | None = None
    priority: str | None = None
    action: str = "continue"
    warn: bool = False

class GuardRules:
    """Deterministic, config-backed L0 escalation and PII guardrails."""
    def __init__(self, root: Path):
        self.root = root
        self.config = yaml.safe_load((root / "config/escalation_rules.yaml").read_text(encoding="utf-8"))
        self.patterns = {name: [re.compile(p, re.I) for p in data.get("patterns", [])]
                         for name, data in self.config["rules"].items()}

    def matches(self, rule: str, text: str) -> bool:
        return any(p.search(text) for p in self.patterns.get(rule, []))

    def classify(self, text: str, *, sentiment: str = "neutral", unmatched_high_risk: bool = False,
                 frustration_loop: bool = False, status_authorized: bool = True) -> GuardResult:
        t = text.strip()
        # Priority order reflects the highest impact independent of query wording.
        if self.matches("R8", t): return GuardResult("distress", "P1", "support")
        lost = self.matches("R4_MONEY", t)
        money = lost and self.matches("R4_ACCESS", t)
        hostile = sentiment == "angry" or (self.matches("R2", t) and not re.search(r"\bnot\s+(?:angry|furious|upset)\b", t, re.I))
        if self.matches("R3", t): return GuardResult("legal_threat", "P1", "escalate")
        if money: return GuardResult("payment_issue", "P1" if hostile else "P2", "kb_first_aid_ticket")
        if self.matches("R5", t) and (lost or hostile):
            return GuardResult("fraud_with_loss", "P1" if money else "P2", "escalate")
        if hostile: return GuardResult("anger", "P2", "escalate")
        if self.matches("R6_ACTION", t): return GuardResult("refund_action", "P2", "escalate")
        if any(p.search(t) for p in _PII_PATTERNS): return GuardResult("sensitive_data", "P2", "warn")
        if frustration_loop: return GuardResult("frustration_loop", "P3", "escalate")
        if unmatched_high_risk: return GuardResult("unmatched_high_risk", "P3", "escalate")
        if self.matches("R11", t) and not status_authorized:
            return GuardResult("identity_mismatch", "P3", "escalate")
        if self.matches("R5", t): return GuardResult("fraud_question", "P3", "offer_human")
        if self.matches("R1", t): return GuardResult("human_request", "P3", "escalate")
        if self.matches("R6_POLICY", t): return GuardResult()
        return GuardResult()

_PII_PATTERNS = [
    re.compile(r"(?i)\b(?:otp|one[- ]time password)\s*[:=-]?\s*[A-Z0-9]{4,8}\b"),
    re.compile(r"(?i)\b(?:cvv|cvc)\s*[:=-]?\s*\d{3,4}\b"),
    re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
    re.compile(r"(?i)\b(?:password|passwd|passcode)\s*[:=-]\s*\S+"),
    re.compile(r"(?i)\b(?:aadhaar|aadhar|pan)\s*(?:no\.?|number)?\s*[:=-]?\s*[A-Z0-9 -]{8,16}\b"),
    re.compile(r"(?<!\d)\+?\d[\d -]{8,14}\d(?!\d)"),
]
def mask_pii(text: str) -> str:
    masked = text
    for pattern in _PII_PATTERNS:
        masked = pattern.sub("[REDACTED]", masked)
    return masked
