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
    r"\b(?:make|write|give|create)\b.{0,25}\b(?:a\s+)?(?:fake|false)\s+promise\b.{0,60}\b(refund|returned|fee|money)\b",
    r"\b(rules|niyam)\b.{0,30}\b(ignore|bhool)\b.{0,80}\b(refund|vaada|waada)\b",
    r"\b(ignore|disregard)\b.{0,50}\b(rules|instructions|niyam)\b.{0,80}\b(refund|vaada|waada)\b",
    r"\b(refund|paise|paisa)\b.{0,25}\b(vaada|waada)\b",
    r"\b(?:pretend|act as|become)\b.{0,50}\b(founder|admin|developer|unrestricted)\b.{0,60}\b(guarantee|promise|approve|stipend|job)\b",
    r"\b(?:output|write|share|reveal|print|show)\b.{0,40}\b(private|system|hidden|secret)\b.{0,25}\b(prompt|key|instructions|rules)\b",
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
    r"\b(?:update|change|edit)\s+(?:my\s+)?(?:PAN|Aadhaar|passport)\s+(?:card|information|details)\b",
    r"\bcorporate\s+batch\s+proposal\b",
    r"\bbusiness\s+deal\b.{0,40}\buniversit(?:y|ies)\b",
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
        related_ids: list[str] = []
        ambiguity_limit = float(config.decision.get("ambiguity_margin", 0.10))
        topics = _distinct_topics(message)
        explicit_multi_topic = len(topics) >= 2 and bool(
            re.search(r"\b(and|also|plus|as well as|aur|par|but)\b", message, re.IGNORECASE)
        )
        close_cross_topic = (
            len(topics) >= 2
            and first.category != second.category
            and retrieval.margin < ambiguity_limit
        )
        if explicit_multi_topic or close_cross_topic:
            return QueryDecision(
                decision=Decision.CLARIFY,
                reason_code="cross_category_ambiguity",
                confidence=retrieval.confidence,
                candidate_ids=[candidate.id for candidate in retrieval.candidates[:3]],
            )
        refund_flow = bool(re.search(
            r"\bregular batch\b.{0,60}\b(?:refund|cancel|cancellation|money back)\b",
            message, re.IGNORECASE,
        ))
        first_terms = set(re.findall(r"[a-z0-9]+", str(top_entry.get("question", "")).casefold()))
        second_terms = set(re.findall(r"[a-z0-9]+", str(entries.get(second.id, {}).get("question", "")).casefold()))
        generic = {"what", "how", "do", "i", "the", "a", "an", "is", "are", "to", "for", "and", "after", "before", "my", "me", "you", "your", "can", "there", "which"}
        first_terms -= generic; second_terms -= generic
        overlap = len(first_terms & second_terms) / max(len(first_terms | second_terms), 1)
        distinct_meaning = overlap < 0.30
        if retrieval.margin < ambiguity_limit and distinct_meaning and not refund_flow:
            second_entry = entries.get(second.id, {})
            same_category_safe = (
                first.category == second.category
                and top_entry.get("risk_level") != "high"
                and second_entry.get("risk_level") != "high"
            )
            if same_category_safe:
                related_ids = [
                    candidate.id for candidate in retrieval.candidates[1:]
                    if candidate.category == first.category
                    and entries.get(candidate.id, {}).get("risk_level") != "high"
                ][:2]
            else:
                return QueryDecision(
                    decision=Decision.CLARIFY,
                    reason_code="low_margin_entry_conflict",
                    confidence=retrieval.confidence,
                    candidate_ids=[first.id, second.id],
                )
    else:
        refund_flow = False
        related_ids = []

    if retrieval.confidence >= t_answer and (retrieval.margin >= t_margin or refund_flow or related_ids):
        return QueryDecision(
            decision=Decision.ANSWER,
            reason_code="high_risk_answer_threshold_met" if high_risk else "answer_threshold_met",
            confidence=retrieval.confidence,
            candidate_ids=[first.id],
            related_ids=related_ids,
        )

    return QueryDecision(
        decision=Decision.NO_MATCH,
        reason_code="answer_threshold_not_met",
        confidence=retrieval.confidence,
        candidate_ids=[candidate.id for candidate in retrieval.candidates[:3]],
    )


def compose_clarification(
    language: str,
    message: str,
    candidate_ids: list[str],
    entries: dict[str, dict],
) -> str:
    questions: list[str] = []
    query_key = " ".join(re.findall(r"[a-z0-9]+", message.casefold()))
    for entry_id in dict.fromkeys(candidate_ids):
        question = str(entries.get(entry_id, {}).get("question", "")).strip()
        question_key = " ".join(re.findall(r"[a-z0-9]+", question.casefold()))
        if question_key and question_key != query_key and question not in questions:
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


def no_match_reply(language: str = "English", query: str = "", help_link: str = "") -> str:
    clean = query.strip().rstrip("?.! ")
    lowered = clean.casefold()
    injection_pattern = r"\b(ignore|disregard|forget)\b.{0,40}\b(rules|instructions|policy)\b|\b(rules|instructions|policy)\b.{0,40}\b(ignore|disregard|forget)\b|\b(promise.{0,30}refund|refund.{0,30}promise)\b"
    if re.search(injection_pattern, lowered):
        topic_en, topic_hi = "a refund outcome", "refund ke result"
    elif re.search(r"\b(college|campus).{0,30}\b(partnership|partner|collaborat)|\b(partnership|partner|collaborat).{0,30}\b(college|campus)", lowered):
        topic_en, topic_hi = "college partnerships", "college partnership"
    elif "istudio technologies" in lowered:
        topic_en, topic_hi = "whether iStudio is affiliated with another company", "iStudio aur doosri company ke sambandh"
    elif re.search(r"\b(aicte|ugc|nsdc)\b", lowered):
        topic_en, topic_hi = "AICTE, UGC, or NSDC approval", "AICTE, UGC ya NSDC approval"
    else:
        topic = clean[:70] or "your question"
        topic_en, topic_hi = topic, topic
    english_link = f" iStudio help center: {help_link}." if help_link else ""
    hinglish_link = f" iStudio help center: {help_link}." if help_link else ""
    injection = bool(re.search(injection_pattern, lowered))
    if language == "Hinglish":
        if injection:
            return ("Main refund ya kisi outcome ka vaada nahi kar sakta. Refund ke rules batch ke hisaab se alag ho sakte hain. "
                    "Aap Regular batch mein hain ya Refund program batch mein? Main iCAT, fees, certificates, refunds aur training ya internship dashboard mein madad kar sakta hoon."
                    f"{hinglish_link} Kya main aapko support team se connect karun?")
        return f"{topic_hi} ke baare mein pakki jaankari mere paas nahi hai. Main iCAT, fees, certificates, refunds aur training ya internship dashboard mein madad kar sakta hoon.{hinglish_link} Kya main aapko support team se connect karun?"
    if language == "Hindi":
        return f"मुझे {topic_en} की पुष्टि की हुई जानकारी नहीं है। मैं iCAT, fees, certificates, refunds और training या internship dashboard में मदद कर सकता हूँ।{hinglish_link} क्या मैं आपको support team से जोड़ दूँ?"
    if injection:
        return ("I can't promise a refund or any outcome. Refund rules can depend on your batch. Are you in the Regular batch or the Refund Guarantee Program batch? "
                "I can help with iCAT, fees, certificates, refunds, and the training or internship dashboard."
                f"{english_link} Would you like me to connect you with the support team?")
    return f"I don't have confirmed details on {topic_en}. I can help with iCAT, fees, certificates, refunds, and the training or internship dashboard.{english_link} Would you like me to connect you with the support team?"
