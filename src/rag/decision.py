from __future__ import annotations

import re

from .config import RagConfig
from .models import Decision, QueryDecision
from .normalize import normalize_text
from .retriever import RetrievalOutput

INJECTION_PATTERNS = (
    r"\bignore\b.{0,40}\b(rules|instructions|system|prompt)\b",
    r"\b(bypass|override)\b.{0,40}\b(knowledge base|rules|instructions|safety)\b",
    r"\b(print|show|reveal|repeat)\b.{0,30}\b(instructions|system prompt|rules)\b",
    r"\bDAN\b",
    r"\bpromise\b.{0,30}\b(refund|money)\b",
    r"\bact as\b.{0,20}\b(unrestricted|developer|admin)\b",
)

OUT_OF_SCOPE_PATTERNS = (
    r"\b(partnership|tie[- ]?ups?|mou|memorandum of understanding|training partner|"
    r"corporate partner|bulk pricing|bulk deals|bulk seats|college seats|onboard our college)\b",
    r"\b(stock price|share price|stock market|current price of .{0,30} stock)\b",
    r"\b(exam timetable|exam schedule at|university exam timetable)\b",
    r"\b(convolutional neural network|neural network|machine learning model)\b",
    r"\b(job offer|offer letter)\b.{0,30}\b(from|by)\s+[A-Z][A-Za-z0-9&.-]+",
)


def is_prompt_injection(message: str) -> bool:
    return any(re.search(pattern, message, re.IGNORECASE) for pattern in INJECTION_PATTERNS)


def is_out_of_scope(message: str) -> bool:
    return any(re.search(pattern, message, re.IGNORECASE) for pattern in OUT_OF_SCOPE_PATTERNS)


def decide(
    message: str,
    retrieval: RetrievalOutput,
    entries: dict[str, dict],
    config: RagConfig,
) -> QueryDecision:
    if is_prompt_injection(message):
        return QueryDecision(
            decision=Decision.NO_MATCH,
            reason_code="prompt_injection_blocked",
            confidence=0.0,
            candidate_ids=[candidate.id for candidate in retrieval.candidates[:3]],
        )
    if is_out_of_scope(message):
        return QueryDecision(
            decision=Decision.NO_MATCH,
            reason_code="out_of_scope_request",
            confidence=0.0,
            candidate_ids=[candidate.id for candidate in retrieval.candidates[:3]],
        )
    if retrieval.query_token_count <= int(config.decision.get("clarify_token_limit", 1)):
        return QueryDecision(
            decision=Decision.CLARIFY,
            reason_code="query_too_vague",
            confidence=retrieval.confidence,
            candidate_ids=[candidate.id for candidate in retrieval.candidates[:3]],
        )
    if not retrieval.candidates:
        return QueryDecision(
            decision=Decision.NO_MATCH,
            reason_code="no_candidates",
            confidence=0.0,
        )

    first = retrieval.candidates[0]
    top_entry = entries[first.id]
    high_risk = top_entry.get("risk_level") == "high"
    t_answer = float(
        config.thresholds["answer_high"] if high_risk else config.thresholds["answer"]
    )
    t_low = float(config.thresholds["low"])
    t_margin = float(config.thresholds["margin"])
    semantic_floor = float(config.retrieval.get("min_semantic_agreement", 0.30))

    if retrieval.confidence < t_low or not retrieval.lexical_agreement:
        return QueryDecision(
            decision=Decision.NO_MATCH,
            reason_code="below_low_threshold" if retrieval.confidence < t_low else "no_lexical_agreement",
            confidence=retrieval.confidence,
            candidate_ids=[candidate.id for candidate in retrieval.candidates[:3]],
        )
    if retrieval.semantic_available and first.semantic_score < semantic_floor:
        return QueryDecision(
            decision=Decision.NO_MATCH,
            reason_code="no_semantic_agreement",
            confidence=retrieval.confidence,
            candidate_ids=[candidate.id for candidate in retrieval.candidates[:3]],
        )

    if len(retrieval.candidates) >= 2:
        second = retrieval.candidates[1]
        if (
            first.category != second.category
            and retrieval.margin < float(config.decision.get("ambiguity_margin", 0.10))
        ):
            return QueryDecision(
                decision=Decision.CLARIFY,
                reason_code="cross_category_ambiguity",
                confidence=retrieval.confidence,
                candidate_ids=[candidate.id for candidate in retrieval.candidates[:3]],
            )

    if retrieval.confidence >= t_answer and retrieval.margin >= t_margin:
        return QueryDecision(
            decision=Decision.ANSWER,
            reason_code="high_risk_answer_threshold_met" if high_risk else "answer_threshold_met",
            confidence=retrieval.confidence,
            candidate_ids=[candidate.id for candidate in retrieval.candidates[:2]],
        )

    return QueryDecision(
        decision=Decision.NO_MATCH,
        reason_code="answer_threshold_not_met",
        confidence=retrieval.confidence,
        candidate_ids=[candidate.id for candidate in retrieval.candidates[:3]],
    )


def compose_clarification(
    language: str,
    candidate_ids: list[str],
    entries: dict[str, dict],
) -> str:
    questions: list[str] = []
    for entry_id in candidate_ids:
        question = str(entries.get(entry_id, {}).get("question", "")).strip()
        if question and question not in questions:
            questions.append(question.rstrip("?"))
        if len(questions) == 3:
            break
    if not questions:
        questions = [
            "What is the program fee?",
            "How do I access my account?",
            "How do I verify a certificate?",
        ]
    if len(questions) == 1:
        choices = questions[0]
    else:
        choices = " or ".join(questions)
    if language == "Hinglish":
        response = f"Aap kis baare mein pooch rahe hain: {choices}?"
    elif language == "Hindi":
        response = f"Aap kis baat ke baare mein pooch rahe hain: {choices}?"
    else:
        response = f"Which detail do you need: {choices}?"
    return response[:600]


def no_match_reply() -> str:
    return (
        "I do not have this information in the current knowledge base. "
        "I can connect a team member."
    )
