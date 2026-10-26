"""Synthetic, explicitly demo-only conversations for the local demo database."""

DEMO_CONVERSATIONS = [
    {
        "seed_key": "payment-access-en", "priority": "P1", "language": "English", "reason_code": "payment_issue", "intent": "payment_access", "status": "open", "kb_ids_tried": ["CAT-013"], "confidence": .88,
        "summary_3_lines": ["Payment debit reported.", "Portal access is still missing.", "Customer was advised of the 24-hour update window."],
        "suggested_reply": "SAMPLE DATA — Please share the receipt and registered email so the team can check the payment.",
        "turns": [{"role":"customer","text":"My payment was deducted but I still cannot access the portal."},{"role":"assistant","text":"SAMPLE DATA — The dashboard can take up to 24 hours to update. If access is still missing after that, email the receipt or screenshot and registered email to contact@internshipstudio.com, or call 7507869003."}],
    },
    {
        "seed_key": "refund-batch-en", "priority": "P2", "language": "English", "reason_code": "refund_request", "intent": "refund", "status": "open", "kb_ids_tried": ["CAT-047","CAT-048"], "confidence": .81,
        "summary_3_lines": ["Customer asked about a refund.", "Batch type is not known.", "Need Regular vs Refund-program clarification."],
        "suggested_reply": "SAMPLE DATA — Are you in the Regular batch or the Refund program batch?",
        "turns": [{"role":"customer","text":"I want a refund. Will I get my money back?"},{"role":"assistant","text":"SAMPLE DATA — Before I answer, are you in the Regular batch or the Refund program batch?"}],
    },
    {
        "seed_key": "approval-trust-en", "priority": "P2", "language": "English", "reason_code": "trust_verification", "intent": "certificate_approval", "status": "open", "kb_ids_tried": ["CAT-019"], "confidence": .91,
        "summary_3_lines": ["Customer asked about approval status.", "No confirmed AICTE/UGC/NSDC information is available.", "Human follow-up requested."],
        "suggested_reply": "SAMPLE DATA — The team can confirm the applicable information.",
        "turns": [{"role":"customer","text":"Is this certificate AICTE approved?"},{"role":"assistant","text":"SAMPLE DATA — I do not have confirmed information about AICTE approval. iStudio describes its certificates as ISO-verified; that does not establish AICTE approval. Would you like me to connect you with the team?"}],
    },
    {
        "seed_key": "certificate-delay-en", "priority": "P3", "language": "English", "reason_code": "certificate_status", "intent": "certificate", "status": "open", "kb_ids_tried": ["CAT-021","CAT-053"], "confidence": .76,
        "summary_3_lines": ["Customer reports a delayed certificate.", "Current individual status is unknown.", "Team confirmation requested."],
        "suggested_reply": "SAMPLE DATA — The team can check your certificate status.",
        "turns": [{"role":"customer","text":"My internship certificate has not arrived."},{"role":"assistant","text":"SAMPLE DATA — I cannot confirm the individual certificate status here. Would you like me to ask the team to check it?"}],
    },
    {
        "seed_key": "video-load-hi", "priority": "P3", "language": "Hinglish", "reason_code": "technical_access", "intent": "video_access", "status": "open", "kb_ids_tried": ["CAT-025"], "confidence": .79,
        "summary_3_lines": ["Learner reports training video loading issue.", "Basic troubleshooting was shared.", "Ticket remains open for follow-up."],
        "suggested_reply": "SAMPLE DATA — Agar issue continue ho, screenshot aur registered email share karein.",
        "turns": [{"role":"customer","text":"Videos load nahi ho rahe, kya karun?"},{"role":"assistant","text":"SAMPLE DATA — Page refresh karke aur stable internet par dobara try karein. Agar issue continue ho, kya main aapko support team se connect kar doon?"}],
    },
    {
        "seed_key": "referral-missing-en", "priority": "P3", "language": "English", "reason_code": "referral_issue", "intent": "referral", "status": "resolved", "kb_ids_tried": ["CAT-064"], "confidence": .72,
        "summary_3_lines": ["Referral was not recorded.", "Team follow-up was requested.", "Demo ticket is marked resolved."],
        "suggested_reply": "SAMPLE DATA — The support team can verify referral records.",
        "turns": [{"role":"customer","text":"My referral did not show up."},{"role":"assistant","text":"SAMPLE DATA — I cannot verify referral status here. The team can check it if you share the registered email."}],
    },
    {
        "seed_key": "college-partnership-hi", "priority": "P3", "language": "Hinglish", "reason_code": "kb_gap", "intent": "college_partnership", "status": "open", "kb_ids_tried": [], "confidence": .22,
        "summary_3_lines": ["College partnership information was requested.", "No matching KB answer is available.", "Demo record includes a human follow-up."],
        "suggested_reply": "SAMPLE DATA — College partnership details available nahi hain. Kya main aapko team se connect kar doon?",
        "turns": [{"role":"customer","text":"Hamare college ke saath partnership karni hai."},{"role":"assistant","text":"SAMPLE DATA — College partnership details mere paas nahi hain. Kya main aapko team se connect kar doon?"}],
    },
    {
        "seed_key": "receipt-followup-en", "priority": "P3", "language": "English", "reason_code": "payment_receipt", "intent": "receipt", "status": "resolved", "kb_ids_tried": ["CAT-014"], "confidence": .83,
        "summary_3_lines": ["Customer asked where to find a payment receipt.", "Confirmation email and spam folder were suggested.", "Demo ticket is resolved."],
        "suggested_reply": "SAMPLE DATA — Check the confirmation email and spam folder.",
        "turns": [{"role":"customer","text":"Where can I find my payment receipt?"},{"role":"assistant","text":"SAMPLE DATA — Check your confirmation email and spam folder. If payment is still missing from the dashboard after 24 hours, the team can check the receipt."}],
    },
    {
        "seed_key": "icat-id-hi", "priority": "P2", "language": "Hinglish", "reason_code": "icat_access", "intent": "icat_login", "status": "open", "kb_ids_tried": ["CAT-036"], "confidence": .74,
        "summary_3_lines": ["Learner cannot find the iCAT ID or exam link.", "Individual access details are not confirmed.", "Support follow-up requested."],
        "suggested_reply": "SAMPLE DATA — Registered email share karein, team access check kar sakti hai.",
        "turns": [{"role":"customer","text":"Mera iCAT ID aur link nahi mil raha."},{"role":"assistant","text":"SAMPLE DATA — Main aapka individual iCAT ID confirm nahi kar sakta. Kya main team se check karwa doon?"}],
    },
    {
        "seed_key": "placement-terms-en", "priority": "P2", "language": "English", "reason_code": "placement_terms", "intent": "placement", "status": "open", "kb_ids_tried": ["CAT-044"], "confidence": .86,
        "summary_3_lines": ["Customer asked whether placement is guaranteed.", "Available wording describes assistance, not a guaranteed outcome.", "Team confirmation offered."],
        "suggested_reply": "SAMPLE DATA — Placement assistance is described; no outcome is guaranteed.",
        "turns": [{"role":"customer","text":"Does the program guarantee a job?"},{"role":"assistant","text":"SAMPLE DATA — The available wording describes placement assistance, not a guaranteed outcome. Would you like me to connect you with the team?"}],
    },
    {
        "seed_key": "refund-conditions-hi", "priority": "P2", "language": "Hinglish", "reason_code": "refund_conditions", "intent": "refund_program", "status": "open", "kb_ids_tried": ["CAT-048"], "confidence": .78, "batch_type": "refund_program",
        "summary_3_lines": ["Learner asked about Refund Program conditions.", "Eligibility must be checked against the applicable batch conditions.", "Human follow-up offered."],
        "suggested_reply": "SAMPLE DATA — Team eligibility aur batch details verify kar sakti hai.",
        "turns": [{"role":"customer","text":"Refund program ki conditions kya hain?"},{"role":"assistant","text":"SAMPLE DATA — Conditions aur eligibility batch ke hisaab se verify karni hoti hai. Kya main team se confirm karwa doon?"}],
    },
    {
        "seed_key": "extension-en", "priority": "P4", "language": "English", "reason_code": "extension_info", "intent": "extension", "status": "resolved", "kb_ids_tried": ["CAT-055"], "confidence": .71,
        "summary_3_lines": ["Customer asked how to request an extension.", "Available KB says duration may extend up to six months; process and charges are not stated.", "Demo ticket is resolved."],
        "suggested_reply": "SAMPLE DATA — The team can confirm the extension process and charges.",
        "turns": [{"role":"customer","text":"How do I request an extension?"},{"role":"assistant","text":"SAMPLE DATA — The duration may be extended up to six months. The request steps and charges are not stated; the team can confirm them."}],
    },
    {
        "seed_key": "portal-delay-en", "priority": "P1", "language": "English", "reason_code": "payment_issue", "intent": "portal_access", "status": "open", "kb_ids_tried": ["CAT-013","CAT-051"], "confidence": .89,
        "summary_3_lines": ["Payment is reported complete but portal access is absent.", "24-hour dashboard update window was explained.", "Ticket retained for payment follow-up."],
        "suggested_reply": "SAMPLE DATA — If access is still missing after 24 hours, send the receipt and registered email.",
        "turns": [{"role":"customer","text":"Payment complete hai par portal access nahi aaya."},{"role":"assistant","text":"SAMPLE DATA — Dashboard update hone mein 24 ghante tak lag sakte hain. Uske baad bhi access na aaye toh receipt aur registered email support ko bhejein."}],
    },
    {
        "seed_key": "icat-interruption-en", "priority": "P2", "language": "English", "reason_code": "icat_technical_issue", "intent": "icat_exam", "status": "open", "kb_ids_tried": ["CAT-040"], "confidence": .73,
        "summary_3_lines": ["iCAT stopped during the exam.", "No result or attempt status was guessed.", "Support review requested."],
        "suggested_reply": "SAMPLE DATA — The support team can review the exam issue.",
        "turns": [{"role":"customer","text":"My iCAT stopped halfway through."},{"role":"assistant","text":"SAMPLE DATA — I cannot confirm the attempt status. Would you like me to ask the support team to review it?"}],
    },
    {
        "seed_key": "refund-dispute-hi", "priority": "P1", "language": "Hinglish", "reason_code": "refund_dispute", "intent": "refund_program", "status": "open", "kb_ids_tried": ["CAT-047","CAT-048"], "confidence": .84,
        "summary_3_lines": ["Learner disputes a refund decision.", "No refund outcome was promised.", "Human eligibility review requested."],
        "suggested_reply": "SAMPLE DATA — Team aapki eligibility aur case details verify karegi.",
        "turns": [{"role":"customer","text":"Maine saari conditions poori ki, refund kab milega?"},{"role":"assistant","text":"SAMPLE DATA — Refund ka outcome promise nahi kar sakta. Team batch aur eligibility verify karegi; kya main ticket raise kar doon?"}],
    },
]
