from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest

from src.api.app import create_app
from src.app.store import Store


class _Bot:
    def __init__(self, store):
        self.store = store
        self.engine = SimpleNamespace(
            retriever=SimpleNamespace(kb_hash="test-hash", entries={}),
            config=SimpleNamespace(embedding_model="test-model"),
            provider=SimpleNamespace(name="none"),
        )


def _request(app, method, path, **kwargs):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(run())


@pytest.fixture
def setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("AGENT_API_KEY", "stage8-test-key")
    store = Store(tmp_path, secret="stage8-store-secret")
    app = create_app(bot=_Bot(store), warmup=False)
    return app, store


def test_operations_pages_and_api_route_shadowing(setup_app):
    app, _ = setup_app
    agent = _request(app, "GET", "/agent")
    founder = _request(app, "GET", "/founder")
    assert agent.status_code == 200 and "Agent sign in" in agent.text and "agent.js" in agent.text
    assert founder.status_code == 200 and "Support dashboard" in founder.text and "founder.js" in founder.text
    assert _request(app, "GET", "/health").status_code == 200
    assert _request(app, "GET", "/webhook/meta").status_code == 403
    assert _request(app, "GET", "/api/tickets").status_code == 401
    assert _request(app, "GET", "/api/tickets", headers={"Authorization": "stage8-test-key"}).status_code == 401
    assert _request(app, "GET", "/api/metrics/public").status_code == 200


def test_public_metrics_schema_contains_aggregates_and_no_message_or_identity_data(setup_app):
    app, store = setup_app
    sender_hash = store.sender_hash("synthetic-sender")
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as db:
        db.execute("INSERT INTO messages(sender_hash,role,text,created_at) VALUES(?,?,?,?)", (sender_hash, "customer", "<script>private user query</script>", now))
        db.execute("INSERT INTO messages(sender_hash,role,text,created_at) VALUES(?,?,?,?)", (sender_hash, "assistant", "private assistant answer", now))
        db.execute("INSERT INTO sessions(sender_hash,updated_at,state) VALUES(?,?,?)", (sender_hash, now, json.dumps({"batch_type": "regular"})))
        db.execute("INSERT INTO kb_gaps(sender_hash,query,created_at) VALUES(?,?,?)", (sender_hash, "college partnership details", now))
    response = _request(app, "GET", "/api/metrics/public")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "demo_data", "messages_handled", "auto_resolved_percent", "escalations_by_reason",
        "escalations_by_priority", "average_bot_latency_ms", "top_intents", "kb_gaps",
        "language_split", "batch_type_split", "sla_breaches", "token_cost_per_1000_messages_usd", "token_cost_status",
    }
    rendered = json.dumps(payload).casefold()
    assert "private user query" not in rendered and "private assistant answer" not in rendered
    assert "synthetic-sender" not in rendered and sender_hash not in rendered
    assert "college partnership details" not in rendered
    assert payload["messages_handled"] == 1
    assert payload["auto_resolved_percent"] is None
    assert payload["average_bot_latency_ms"] is None
    assert payload["kb_gaps"] == [{"topic": "college partnerships", "count": 1}]
    assert payload["token_cost_per_1000_messages_usd"] == 0.0
    assert payload["token_cost_status"] == "no_llm_mode"
    store.log_response_metric(12.5, True, datetime.now(timezone.utc))
    measured = _request(app, "GET", "/api/metrics/public").json()
    assert measured["average_bot_latency_ms"] == 12.5
    assert measured["auto_resolved_percent"] == 100.0
    assert all(set(item).issubset({"label", "count", "rate_percent"}) for item in measured["escalations_by_reason"])
    assert all(set(item) == {"topic", "count"} for item in measured["kb_gaps"])
    assert all(set(item) == {"label", "count", "rate_percent"} for item in measured["escalations_by_priority"])
    assert all(set(item) == {"label", "count"} for item in measured["top_intents"])
    assert all(isinstance(value, int) for value in measured["language_split"].values())
    assert all(isinstance(value, int) for value in measured["batch_type_split"].values())
    assert all(isinstance(value, (int, float)) for key, value in measured.items() if key.endswith("_percent") or key.endswith("_ms") or key == "sla_breaches")


def test_agent_key_missing_wrong_key_rate_limit_and_success(setup_app):
    app, _ = setup_app
    assert _request(app, "GET", "/api/tickets").status_code == 401
    missing = _request(app, "POST", "/api/agent/auth", json={"key": "wrong"})
    assert missing.status_code == 401
    assert "tickets" not in missing.text.casefold()
    assert _request(app, "GET", "/api/tickets", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert _request(app, "POST", "/api/agent/auth", json={"key": "stage8-test-key"}).json() == {"authenticated": True}
    for _ in range(10):
        response = _request(app, "POST", "/api/agent/auth", json={"key": "bad"})
        assert response.status_code == 401
    limited = _request(app, "POST", "/api/agent/auth", json={"key": "bad"})
    assert limited.status_code == 429 and "tickets" not in limited.text.casefold()


def test_agent_transcript_xss_uses_safe_text_sinks_and_key_is_not_persisted(setup_app):
    from pathlib import Path
    app, store = setup_app
    store.open_ticket(store.sender_hash("synthetic"), {
        "ticket_id": "", "reason_code": "kb_gap", "priority": "P3", "status": "open",
        "customer_masked_id": "masked-customer", "language": "English", "intent": "kb_gap",
        "summary_3_lines": ["Sample line 1", "Sample line 2", "Sample line 3"],
        "last_5_turns": [{"role": "customer", "text": "<script>alert(1)</script>"}],
        "kb_ids_tried": [], "confidence": 0.0, "suggested_reply": "We can ask the team.",
        "sla_deadline": "Tue 27 Oct, 11:00 AM IST", "created_at": datetime.now(timezone.utc).isoformat(),
    })
    response = _request(app, "GET", "/api/tickets", headers={"Authorization": "Bearer stage8-test-key"})
    assert response.status_code == 200
    assert "<script>alert(1)</script>" in response.text
    source = Path("frontend/agent.js").read_text(encoding="utf-8")
    page = Path("frontend/agent.html").read_text(encoding="utf-8")
    assert "innerHTML" not in source and "textContent" in source
    assert 'el("p", turn.text)' in source
    assert "localStorage" not in source and "sessionStorage" not in source
    assert "Authorization" in source and "Bearer ${agentKey}" in source
    assert "<script>" not in page


def test_demo_database_seeds_at_startup_once(tmp_path, monkeypatch):
    monkeypatch.setenv("ENV", "demo")
    store = Store(tmp_path, secret="startup-seed-secret")
    app = create_app(bot=_Bot(store), warmup=False)

    async def start_twice():
        await app.router.startup()
        await app.router.startup()

    asyncio.run(start_twice())
    with store.connect() as db:
        ticket_count = db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        non_demo = db.execute("SELECT COUNT(*) FROM tickets WHERE json_extract(payload, '$.demo') != 1").fetchone()[0]
    assert ticket_count == 15
    assert non_demo == 0


def test_live_demo_chat_records_are_flagged(tmp_path, monkeypatch):
    monkeypatch.setenv("ENV", "demo")
    store = Store(tmp_path, secret="live-demo-secret")
    sender_hash = store.sender_hash("live-demo")
    now = datetime.now(timezone.utc)
    store.append_message(sender_hash, "sample-1", "customer", "sample", now)
    ticket = store.open_ticket(sender_hash, {
        "ticket_id": "", "reason_code": "demo_reason", "priority": "P3", "status": "open",
        "customer_masked_id": "demo-customer", "language": "English", "intent": "demo",
        "summary_3_lines": ["a", "b", "c"], "last_5_turns": [], "kb_ids_tried": [],
        "confidence": 0.0, "suggested_reply": "sample", "sla_deadline": "Tue 27 Oct, 11:00 AM IST",
        "created_at": now.isoformat(),
    })
    with store.connect() as db:
        message_demo = db.execute("SELECT demo FROM messages").fetchone()[0]
    assert message_demo == 1 and ticket["demo"] is True
