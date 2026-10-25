from __future__ import annotations

from types import SimpleNamespace
import yaml

from src.rag.composer import _fallback_text
from src.rag.config import RagConfig
from src.rag.normalize import detect_language
from src.rag.decision import no_match_reply


def _config():
    return SimpleNamespace(
        decision={"max_reply_chars":600,"show_sample_label":True},
        sample_label_enabled=True,
    )


def test_fee_caveat_is_a_capitalized_sentence_before_final_offer_english():
    entry={
        "answer_rendered":"The fee is Rs 8,500. fees can change, please confirm on the official site before paying. I can connect a team member.",
        "answer_hinglish":"",
        "handoff_offer":True,
        "is_mock":False,
    }
    reply=_fallback_text(entry,_config(),"English")
    assert "The fee is Rs 8,500. Fees can change, so please confirm on the official site before paying." in reply
    assert reply.endswith("Would you like me to connect you with a team member?")
    assert "I can connect" not in reply


def test_fee_caveat_is_a_capitalized_sentence_before_final_offer_hinglish():
    entry={
        "answer_rendered":"",
        "answer_hinglish":"Fee Rs 8,500 hai. fees badal sakti hain; payment se pehle official site par confirm kar lein. Main aapko support team se connect kar sakta hoon.",
        "handoff_offer":True,
        "is_mock":False,
    }
    reply=_fallback_text(entry,_config(),"Hinglish")
    assert "Fee Rs 8,500 hai. Fees badal sakti hain, isliye payment se pehle official site par confirm kar lein." in reply
    assert reply.endswith("Kya main aapko support team se connect kar doon?")
    assert "Main aapko" not in reply


def test_out_of_kb_reply_names_the_college_partnership_topic():
    english=no_match_reply("English","Partnership for our college")
    hinglish=no_match_reply("Hinglish","college ke saath partnership chahiye")
    assert "college partnerships" in english
    assert "college partnership" in hinglish
    assert "this" not in english.casefold()


def test_refund_conflict_is_internal_confirmation_item_only():
    from pathlib import Path
    import yaml
    root=Path(__file__).resolve().parents[1]
    verified=yaml.safe_load((root/"kb/verified_facts.yaml").read_text(encoding="utf-8"))
    report=(root/"docs/kb_report.md").read_text(encoding="utf-8")
    note=verified["verified_facts"]["placeholders"]["REFUND_ATTENDANCE_NOTE"]["value_hinglish"]
    assert "75%" not in note and "100%" not in note
    assert "75%" in report and "confirm" in report.casefold()


def test_company_support_contacts_are_preserved_when_masking_personal_data():
    from src.rag.engine import mask_pii
    from src.guard import mask_pii as guard_mask_pii
    sample="Contact contact@internshipstudio.com or 7507869003. Personal phone +919000000001 and OTP: 123456."
    for mask in (mask_pii,guard_mask_pii):
        reply=mask(sample)
        assert "contact@internshipstudio.com" in reply
        assert "7507869003" in reply
        assert "+919000000001" not in reply
        assert "123456" not in reply


def test_ticket_language_does_not_call_eta_a_promise():
    from pathlib import Path
    messages=yaml.safe_load((Path(__file__).resolve().parents[1]/"config/messages.yaml").read_text(encoding="utf-8"))
    for language in ("english","hinglish"):
        template=messages["escalation"][language]["customer"].casefold()
        assert "{eta}" in template and "aim to reply" in template if language=="english" else "{eta}" in template and "jawab dene ki koshish" in template
        assert "target, not a promise" not in template and "pakka vaada nahi" not in template
