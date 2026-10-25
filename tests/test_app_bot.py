from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from src.app.bot import Bot
from src.app.store import Store

class EngineSpy:
    def __init__(self): self.calls=[]
    def answer(self, text, **kwargs):
        self.calls.append((text, kwargs))
        return None

def test_explicit_handoff_skips_engine_and_dedupes(tmp_path):
    root=Path(__file__).parents[1]
    engine=EngineSpy()
    bot=Bot(root, engine=engine, store=Store(tmp_path, "test-secret"))
    a=bot.handle_message("+919876500001", "Please connect me to a human", "m1", "whatsapp",
                         datetime(2026,10,26,12,tzinfo=ZoneInfo("Asia/Kolkata")))
    b=bot.handle_message("+919876500001", "Please connect me to a human", "m1", "whatsapp",
                         datetime(2026,10,26,12,tzinfo=ZoneInfo("Asia/Kolkata")))
    assert engine.calls == []
    assert a.ticket and a.ticket["priority"] == "P3"
    assert b.ticket["ticket_id"] == a.ticket["ticket_id"]
    assert len(bot.store.list_tickets()) == 1
    assert all(len(msg) <= 600 for msg in a.messages)

def test_payment_issue_uses_extractive_only_engine(tmp_path):
    root=Path(__file__).parents[1]
    engine=EngineSpy()
    bot=Bot(root, engine=engine, store=Store(tmp_path, "test-secret"))
    result=bot.handle_message("+919876500002", "Payment cut gaya par access nahi aaya", "m2", "whatsapp",
                              datetime(2026,10,26,12,tzinfo=ZoneInfo("Asia/Kolkata")))
    assert engine.calls == [("Payment cut gaya par access nahi aaya", {"force_extractive": True})]
    assert result.ticket and result.ticket["reason_code"] == "payment_issue"

def test_store_persists_only_masked_pii(tmp_path):
    store=Store(tmp_path,"test-secret")
    sender=store.sender_hash("+919123456789")
    store.append_message(sender,"pii-1","customer","Phone +919123456789 OTP: 123456 card 4111111111111111",datetime.now())
    store.processed("pii-processed",sender,{"messages":["Phone +919123456789 OTP: 123456 card 4111111111111111"]},datetime.now())
    raw=(tmp_path / "data/app.db").read_bytes()
    for secret in (b"+919123456789",b"123456",b"4111111111111111"):
        assert secret not in raw

def test_corrupt_duplicate_cache_is_a_miss_and_can_be_replaced(tmp_path):
    store=Store(tmp_path,"test-secret")
    with store.connect() as db:
        db.execute("INSERT INTO processed_messages VALUES(?,?,?,?)", ("broken", "sender", "{bad", datetime.now().isoformat()))
    assert store.duplicate("broken") is None
    now=datetime.now()
    store.processed("broken", "sender", {"messages":["recovered"]}, now)
    assert store.duplicate("broken") == {"messages":["recovered"]}
from src.rag.engine import RagEngine
from src.rag.providers import NoneProvider

def test_payment_hinglish_first_aid_uses_rag_and_keeps_language(tmp_path):
    root=Path(__file__).parents[1]
    bot=Bot(root, engine=RagEngine(root,provider=NoneProvider()), store=Store(tmp_path,"test-secret"))
    result=bot.handle_message("+919000000501","Btech web dev internship ka certificate milega kya, payment cut gaya par access nahi aaya","fresh-pay-1","whatsapp")
    assert result.ticket is not None
    assert result.ticket["reason_code"] == "payment_issue", result.debug
    assert result.ticket["language"] == "Hinglish"
    assert result.debug["reason"] == "payment_issue"
    assert "internal_error_type" not in result.debug
    assert any("SAMPLE DATA" in part for part in result.messages)
    assert any("Paisa debit ho gaya hai" in part for part in result.messages)

