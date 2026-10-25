from pathlib import Path
import pytest
from src.guard import GuardRules, mask_pii
from src.app.bot import sla_deadline
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT = Path(__file__).parents[1]
GUARD = GuardRules(ROOT)

@pytest.mark.parametrize("rule,phrases,action", [
("R1", ["Please connect me to a human", "I want to talk to an agent", "Can I speak to a representative", "Transfer me to a real person", "Call me please", "Human please", "Insaan se baat karni hai", "किसी इंसान से बात करनी है"], "escalate"),
("R2", ["You are an idiot", "This is useless", "I am furious", "I am fed up with this", "Your service is stupid", "Gali mat do, this is bakwas", "Bahut gussa aa raha hai", "This is ridiculous!!!"], "escalate"),
("R3", ["I will take this to consumer court", "I am filing a police complaint", "I will report this to cyber crime", "I will send a legal notice", "I am filing a chargeback", "I will report this to RBI", "I will post this on LinkedIn", "कानूनी नोटिस भेजूंगा"], "escalate"),
("R4", ["Payment debited, no access", "Amount deducted, no receipt", "Paise kat gaye, access nahi", "Payment cut, not enrolled", "Money debited, cannot access", "Paisa kat gaya, login nahi", "रकम कट गई, एक्सेस नहीं", "पैसे कट गए, रसीद नहीं"], "kb_first_aid_ticket"),
("R5", ["Is this a scam?", "Is this fake?", "Is this fraud?", "Are you cheating me?", "Yeh fake hai kya?", "Kya yeh fraud hai?", "क्या यह धोखा है?", "Is it a scam or real?"], "offer_human"),
("R6_ACTION", ["I want a refund", "Please refund me", "Give my money back", "Cancel my enrolment", "Refund do please", "Refund chahiye", "Paise wapas karo", "मुझे रिफंड चाहिए"], "escalate"),
("R6_POLICY", ["What is the refund policy?", "Explain refund rules", "Am I eligible for a refund?", "Can I get a refund?", "Refund policy kya hai?", "Refund kab milega?", "रिफंड नीति क्या है?", "रिफंड पॉलिसी बताइए"], "continue"),
("R7", ["OTP: 123456", "CVV: 821", "Card 4111111111111111", "Password: secret123", "Aadhaar number: 1234 5678 9123", "PAN number: ABCDE1234F", "One-time password 930112", "CVC=123"], "warn"),
("R8", ["I want to die", "I am going to kill myself", "I will hurt myself", "I want to end my life", "I will self-harm", "मैं आत्महत्या करूंगा", "मैं आत्महत्या करूंगी", "खुद को मार लूंगा"], "support"),
("R9", ["Need escalation"], "escalate"), ("R10", ["Need escalation"], "escalate"),
("R11", ["payment status", "certificate status", "status of my payment", "where is my certificate", "mera payment status", "certificate kab milega", "payment ka status", "मेरे भुगतान की स्थिति"], "escalate"),
])
def test_guard_positive_cases(rule, phrases, action):
    for phrase in phrases:
        if rule == "R9": got = GUARD.classify(phrase, frustration_loop=True)
        elif rule == "R10": got = GUARD.classify(phrase, unmatched_high_risk=True)
        elif rule == "R11": got = GUARD.classify(phrase, status_authorized=False)
        else: got = GUARD.classify(phrase)
        assert got.action == action, (rule, phrase, got)

@pytest.mark.parametrize("phrase", [
"What is an agent?", "How do I contact support?", "What makes a service useful?",
"What is the consumer court?", "How does a chargeback work?", "What is a refund policy?",
"Can you explain refund eligibility?", "What is an OTP?", "How do I secure my CVV?",
"How does Aadhaar work?", "What are password rules?", "What is suicide prevention?",
"How can I support a friend who feels distressed?", "What is payment status?",
"How do I check certificate availability?", "Payment is paid in full; where is my course access?",
"Please explain scam awareness.", "Is the program fee paid monthly?", "Can I speak with an agent about curriculum?",
"Refund policy kya hai?", "क्या OTP सुरक्षित है?", "मेरा प्रमाणपत्र कब मिलेगा?", "RBI kya hota hai?",
"Not angry, what is refund policy?", "What does human agent mean?"
])
def test_information_questions_do_not_escalate(phrase):
    result = GUARD.classify(phrase)
    assert result.action not in {"escalate", "kb_first_aid_ticket", "support", "warn"}

@pytest.mark.parametrize("raw", ["+919876543210", "OTP: 123456", "CVV: 821", "4111111111111111", "Password: secret123", "Aadhaar: 1234 5678 9123", "PAN: ABCDE1234F"])
def test_mask_pii_removes_sensitive_seed_values(raw):
    clean = mask_pii(raw)
    assert "[REDACTED]" in clean
    assert raw.split(": ")[-1] not in clean

def test_sla_skips_closed_hours_and_sunday():
    ist = ZoneInfo("Asia/Kolkata")
    got = sla_deadline(datetime(2026, 10, 25, 20, 30, tzinfo=ist), "P2", 1)
    assert got == datetime(2026, 10, 26, 12, 0, tzinfo=ist)


@pytest.mark.parametrize(
    ("phrase", "reason", "priority", "action"),
    [
        ("I paid twice by mistake", "duplicate_payment", "P2", "kb_first_aid_ticket"),
        ("My payment is duplicated", "duplicate_payment", "P2", "kb_first_aid_ticket"),
        ("I got billed two times for one registration", "duplicate_payment", "P2", "kb_first_aid_ticket"),
        ("Can our college partner with you?", "out_of_scope", None, "offer_human"),
        ("A corporate collaboration inquiry", "out_of_scope", None, "offer_human"),
        ("Is your office in Pune or Ahmednagar?", "location_conflict", "P3", "escalate"),
        ("Where is the Internship Studio office?", "location_conflict", "P3", "escalate"),
        ("What are iStudio Plus placement terms?", "istudio_plus_human", "P3", "escalate"),
    ],
)
def test_company_specific_handoff_rules(phrase, reason, priority, action):
    result = GUARD.classify(phrase)
    assert (result.reason_code, result.priority, result.action) == (reason, priority, action)

@pytest.mark.parametrize("rule,phrases,context", [
("R1", ["What is an agent?", "How does a representative work?", "Can you explain human review?", "What does real person mean?", "Where can I read about agents?"], {}),
("R2", ["What is the issue?", "I am not angry about this.", "Please explain the process.", "I need help with enrollment.", "This is an urgent question."], {}),
("R3", ["What is consumer court?", "How does chargeback work?", "What is a legal notice?", "What does RBI regulate?", "Where can I read about police complaints?"], {}),
("R4", ["What happens after payment?", "I paid and my access works.", "How do I pay the fee?", "Where is the receipt section?", "I am asking about the enrollment process."], {}),
("R5", ["How can I identify a scam?", "What does fraud mean?", "Explain fake websites.", "Where to report online fraud generally?", "What is scam awareness?"], {}),
("R6", ["What is the refund policy?", "Explain refund eligibility.", "How long does cancellation take?", "What are refund rules?", "Can you explain the refund process?"], {}),
("R7", ["What is an OTP?", "How do I secure a CVV?", "What is Aadhaar?", "How should I make a password?", "What is a PAN card?"], {}),
("R8", ["What is suicide prevention?", "How can I help a friend in crisis?", "Explain self-harm support.", "Where can people find mental-health help?", "What is a crisis plan?"], {}),
("R9", ["What is the fee?", "Tell me about the track.", "How long is the course?", "I need certificate information.", "What are program dates?"], {"frustration_loop":False}),
("R10", ["What is the fee?", "Tell me about the track.", "How long is the course?", "I need certificate information.", "What are program dates?"], {"unmatched_high_risk":False}),
("R11", ["What is payment status?", "Where is my certificate status?", "How do learners check progress?", "What does a payment record show?", "How do I check my own certificate?"], {"status_authorized":True}),
])
def test_each_rule_has_five_negative_information_cases(rule, phrases, context):
    for phrase in phrases:
        result = GUARD.classify(phrase, **context)
        assert result.action not in {"escalate", "kb_first_aid_ticket", "support", "warn"}, (rule, phrase, result)

@pytest.mark.parametrize("rule,phrases", [
("R9", ["What is the fee?", "Tell me about the track.", "How long is the course?", "I need certificate information.", "What are program dates?", "How does payment work?", "Can I learn about eligibility?", "Is the course online?"]),
("R10", ["corporate partnership proposal", "unlisted payment dispute", "unknown exam result question", "external course accreditation", "job guarantee claim", "financial aid not listed", "unknown refund transfer request", "third-party scholarship status"]),
])
def test_r9_r10_have_eight_positive_trigger_cases(rule, phrases):
    for phrase in phrases:
        context = {"frustration_loop":True} if rule == "R9" else {"unmatched_high_risk":True}
        assert GUARD.classify(phrase, **context).action == "escalate"

