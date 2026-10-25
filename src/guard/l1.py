from __future__ import annotations
import re
from typing import Any

SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type":"string"},
        "language": {"type":"string","enum":["English","Hinglish","Hindi"]},
        "sentiment": {"type":"string","enum":["neutral","positive","negative","angry"]},
        "urgency": {"type":"string","enum":["low","normal","high","urgent"]},
        "needs_human": {"type":"boolean"},
        "confidence": {"type":"number"},
    },
    "required":["intent","language","sentiment","urgency","needs_human","confidence"],
}

class L1Classifier:
    """One-shot JSON intent hint; heuristic fallback is conservative."""
    def classify(self, text: str, provider=None, timeout: float = 2.0) -> dict[str, Any]:
        if provider is not None:
            try:
                raw, _usage = provider.generate_json(
                    "Classify the support message. Return only the required JSON. Never answer the customer.",
                    text[:600], SCHEMA, min(2.0, timeout)
                )
                confidence = float(raw.get("confidence", 0))
                if not 0 <= confidence <= 1: raise ValueError("confidence outside range")
                return {"intent":str(raw["intent"]),"language":raw["language"],"sentiment":raw["sentiment"],
                        "urgency":raw["urgency"],"needs_human":bool(raw["needs_human"]),"confidence":confidence,
                        "source":"llm"}
            except Exception:
                pass
        lower = text.casefold()
        needs = bool(re.search(r"\b(urgent|emergency|supervisor|manager|complaint|not resolved|still not working)\b", lower))
        urgency = "urgent" if re.search(r"\b(emergency|urgent|immediately)\b", lower) else ("high" if needs else "normal")
        return {"intent":"support_request" if needs else "general_question","language":"English",
                "sentiment":"negative" if needs else "neutral","urgency":urgency,
                "needs_human":needs,"confidence":0.55 if needs else 0.4,"source":"heuristic"}


def merge_l1(l0_escalate: bool, l1: dict[str, Any], threshold: float = 0.8) -> bool:
    """L1 may add an escalation; it can never cancel L0."""
    return bool(l0_escalate or (l1.get("needs_human") and float(l1.get("confidence", 0)) >= threshold))