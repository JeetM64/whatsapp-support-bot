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


def test_refund_flow_clarifies_batch_and_persists_selection(tmp_path):
    from types import SimpleNamespace

    class RefundEngine:
        def __init__(self):
            self.calls = []
            self.retriever = SimpleNamespace(entries={
                "CAT-047": {"question": "Regular batch refund policy"},
                "CAT-048": {"question": "Refund Guarantee Program conditions"},
            }, retrieve=lambda text: None)
            self.provider = NoneProvider()

        def answer(self, text, **kwargs):
            self.calls.append(text)
            entry_id = "CAT-048" if "Guarantee Program" in text else "CAT-047"
            return SimpleNamespace(
                decision=SimpleNamespace(value="ANSWER"),
                entries=[SimpleNamespace(id=entry_id, category="refunds", is_mock=False)],
                reply=f"Policy for {entry_id}", language="English", confidence=0.9,
                reason_code="test", degraded=False, latency_ms=1,
                verifier=SimpleNamespace(passed=True), usage=SimpleNamespace(model_dump=lambda: {}),
                estimated_cost_usd=0.0, timings_ms={}, mode="extractive",
            )

    now = datetime(2026, 10, 26, 12, tzinfo=ZoneInfo("Asia/Kolkata"))
    store = Store(tmp_path, "test-secret")
    engine = RefundEngine()
    bot = Bot(Path(__file__).parents[1], engine=engine, store=store)
    first = bot.handle_message("+919876500010", "I want a refund", "refund-1", "whatsapp", now)
    assert "Regular batch or the Refund program batch?" in " ".join(first.messages)
    assert engine.calls == []
    sender_hash = store.sender_hash("+919876500010")
    state = store.get_session(sender_hash, now)
    assert state["pending_refund_batch"] is True
    second = bot.handle_message("+919876500010", "Regular batch", "refund-2", "whatsapp", now)
    assert engine.calls == ["I am in the Regular batch and want a refund. What is the policy?"]
    state = store.get_session(sender_hash, now)
    assert state["batch_type"] == "regular"
    assert state["pending_refund_batch"] is False
    assert engine.calls == ["I am in the Regular batch and want a refund. What is the policy?"]
    assert any("Policy for CAT-047" in part for part in second.messages)


def test_hinglish_refund_flow_clarifies_batch_in_hinglish(tmp_path):
    bot = Bot(
        Path(__file__).parents[1],
        engine=None,
        store=Store(tmp_path, "test-secret"),
    )
    result = bot.handle_message("demo-hinglish", "refund milega?", "refund-hi-1", "web")
    assert any("aap Regular batch mein hain ya Refund program batch mein?" in part for part in result.messages)


def test_duplicate_payment_creates_p2_ticket(tmp_path):
    root = Path(__file__).parents[1]
    engine = EngineSpy()
    bot = Bot(root, engine=engine, store=Store(tmp_path, "test-secret"))
    result = bot.handle_message("+919876500011", "I paid twice by mistake", "dup-1", "whatsapp")
    assert result.ticket is not None
    assert result.ticket["reason_code"] == "duplicate_payment"
    assert result.ticket["priority"] == "P2"
    assert engine.calls == [("I paid twice by mistake", {"force_extractive": True})]

