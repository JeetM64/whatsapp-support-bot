from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from .config import RagConfig
from .models import Decision, QueryDecision
from .normalize import normalize_text
from .retriever import RetrievalOutput

INJECTION_PATTERNS = (
    r"\bignore\b.{0,40}\b(rules|instructions|system|prompt)\b",
    r"\b(disregard|ignore)\b.{0,40}\b(policy|policies|rules|instructions|safety)\b",
    r"\b(bypass|override)\b.{0,40}\b(knowledge base|rules|instructions|safety)\b",
    r"\b(forget|ignore)\b.{0,30}\b(safety|rules|instructions)\b.{0,60}\b(say|claim|pretend)\b.{0,40}\b(refund|refunded|approved|guaranteed)\b",
    r"\b(print|show|reveal|repeat)\b.{0,30}\b(instructions|system prompt|rules)\b",
    r"\bDAN\b",
    r"\bpromise\b.{0,30}\b(refund|money)\b",
    r"\b(rules|niyam)\b.{0,30}\b(ignore|bhool)\b.{0,80}\b(refund|vaada|waada)\b",
    r"\b(ignore|disregard)\b.{0,50}\b(rules|instructions|niyam)\b.{0,80}\b(refund|vaada|waada)\b",
    r"\b(refund|paise|paisa)\b.{0,25}\b(vaada|waada)\b",
    r"\bact as\b.{0,20}\b(unrestricted|developer|admin)\b",
)

OUT_OF_SCOPE_PATTERNS = (
    r"\b(partnership|tie[- ]?ups?|mou|memorandum of understanding|training partner|"
    r"corporate partner|bulk pricing|bulk deals|bulk seats|college seats|bulk enrollment|"
    r"bulk enrolment|enrollment rate|enrolment rate|placement cell.{0,30}collaboration|"
    r"campus.{0,40}(training|cohort)|institution.{0,40}(joint program|collaborat)|"
    r"onboard our college|full cohort)\b",
    r"\b(corporate|company|employer|college|campus).{0,30}(partnership|collaborat\w*|partner)\b",
    r"\b(partnership|collaborat\w*|partner).{0,30}(corporate|company|employer|college|campus)\b",
    r"\b(we are a company|our company|employer|recruiter|corporate team).{0,60}\b(hire|recruit|interns|talent)\b",
    r"\b(company|employer|corporate team).{0,40}\b(need|needs|want|wants|looking for).{0,30}\b(interns|students|learners)\b",
    r"\b(stock price|share price|stock market|current price of .{0,30} stock)\b",
    r"\b(exam timetable|exam schedule at|university exam timetable)\b",
    r"\b(convolutional neural network|neural network|machine learning model)\b",
    r"\b(government scholarship|scholarship application)\b",
    r"\b(job offer|offer letter)\b.{0,30}\b(from|by)\s+[A-Z][A-Za-z0-9&.-]+",
)

TOPIC_CUES = {
    "fee": {"fee", "fees", "budget", "cost", "price", "charge", "pricing"},
    "certificate": {"certificate", "certificates", "certifcate", "certificat"},
    "eligibility": {"eligibility", "eligible", "year", "branch", "department"},
    "schedule": {"schedule", "duration", "weekly", "week", "weeks", "timeline"},
    "batch": {"batch", "start", "date", "dates"},
    "payment": {"payment", "pay", "transaction", "txn", "debit", "receipt", "invoice"},
    "access": {"access", "login", "password", "portal", "lms"},
    "project": {"project", "assignment", "submit", "submission"},
    "program": {"domain", "track", "specialization", "course", "program"},
    "placement": {"placement", "career", "job", "offer"},
    "refund": {"refund", "cancel", "return"},
}


@lru_cache(maxsize=512)
def _distinct_topics(message: str) -> frozenset[str]:
    normalized = normalize_text(message, Path(__file__).resolve().parents[2] / "kb" / "lexicon.yaml")
    tokens = set(normalized.split())
    topics = {topic for topic, cues in TOPIC_CUES.items() if tokens & cues}
    if re.search(r"\bwho\s+can\s+apply\b", message, re.IGNORECASE):
        topics.add("eligibility")
    if re.search(r"\bregular batch\b.{0,60}\b(refund|cancel|money back)\b", message, re.IGNORECASE):
        topics.difference_update({"batch", "program"})
    if re.search(r"\brefund (?:guarantee )?program\b", message, re.IGNORECASE) and re.search(
        r"\b(attendance|assignment|project|students|seats|cap|conditions?)\b", message, re.IGNORECASE
    ):
        topics.difference_update({"program", "refund", "project"})
    if re.search(r"\b(payment|transfer|debit).{0,40}\b(dashboard|portal).{0,30}\b(update|reflect\w*|show)\b", message, re.IGNORECASE):
        topics.discard("access")
    # Certificate requirements include completing and submitting a project; that
    # combination is one answerable workflow, not two unrelated requests.
    if topics == {"certificate", "project"}:
        return frozenset()
    return frozenset(topics)


def is_prompt_injection(message: str) -> bool:
    return any(re.search(pattern, message, re.IGNORECASE) for pattern in INJECTION_PATTERNS)


def is_out_of_scope(message: str) -> bool:
    if any(re.search(pattern, message, re.IGNORECASE) for pattern in OUT_OF_SCOPE_PATTERNS):
        return True
    external_program = re.search(
        r"\b(?:internship|program|course|application|offer|dates?)\b", message, re.IGNORECASE
    )
    named_entity = re.search(r"\b[A-Z]{2,}\b", message)
    known_generic = {"UPI", "LMS", "BTECH", "UGC", "AICTE", "NSDC"}
    return bool(external_program and named_entity and named_entity.group(0) not in known_generic)


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
        ambiguity_limit = float(config.decision.get("ambiguity_margin", 0.10))
        if retrieval.margin < ambiguity_limit:
            return QueryDecision(
                decision=Decision.CLARIFY,
                reason_code="low_margin_entry_conflict",
                confidence=retrieval.confidence,
                candidate_ids=[first.id, second.id],
            )
        topics = _distinct_topics(message)
        explicit_multi_topic = len(topics) >= 2 and bool(
            re.search(r"\b(and|also|plus|as well as|aur|par|but)\b", message, re.IGNORECASE)
        )
        close_cross_topic = (
            len(topics) >= 2
            and first.category != second.category
            and retrieval.margin < ambiguity_limit
        )
        if (
            explicit_multi_topic or close_cross_topic
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


def no_match_reply(language: str = "English", query: str = "") -> str:
    clean = query.strip().rstrip("?.! ")
    lowered = clean.casefold()
    if re.search(r"\b(college|campus).{0,30}\b(partnership|partner|collaborat)|\b(partnership|partner|collaborat).{0,30}\b(college|campus)", lowered):
        topic_en, topic_hi = "college partnerships", "college partnership ke baare mein"
    elif "istudio technologies" in lowered:
        topic_en, topic_hi = "whether iStudio is affiliated with another company", "iStudio aur doosri company ke sambandh ke baare mein"
    elif re.search(r"\b(aicte|ugc|nsdc)\b", lowered):
        topic_en, topic_hi = "AICTE, UGC, or NSDC approval", "AICTE, UGC ya NSDC approval ke baare mein"
    else:
        topic_en, topic_hi = (clean[:70] or "this topic"), (clean[:70] or "is topic ke baare mein")
    if language == "Hinglish":
        return f"Mere paas {topic_hi} ki details nahi hain. Kya main aapko human agent se connect kar doon?"
    if language == "Hindi":
        return f"मुझे {topic_en} की जानकारी नहीं है। क्या मैं आपको मानव एजेंट से जोड़ दूँ?"
    return f"I don't have details on {topic_en}. Would you like me to connect you with a human?"
