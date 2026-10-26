from __future__ import annotations

import asyncio
import json

import httpx

from src.api.app import create_app
from src.app.demo_seed import DEMO_CONVERSATIONS
from src.app.store import Store


class _Bot:
    def __init__(self):
        self.engine = type("Engine", (), {
            "retriever": type("Retriever", (), {"kb_hash": "test", "entries": {"CAT-X": {"question": "Refund program"}}})(),
            "config": type("Config", (), {"embedding_model": "test"})(),
            "provider": type("Provider", (), {"name": "none"})(),
        })()

    def handle_message(self, sender, text, message_id, channel):
        result = type("Reply", (), {})()
        result.messages = ["safe reply"]
        result.ticket = None
        result.debug = {"decision": "CLARIFY", "reason_code": "refund_batch_type", "kb_ids": ["CAT-X"], "confidence": .6, "mode": "template"}
        return result


def _request(app, method, path, **kwargs):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(run())


def test_chat_page_headers_clarify_options_and_routes():
    app = create_app(bot=_Bot(), warmup=False)
    page = _request(app, "GET", "/")
    assert page.status_code == 200
    assert "Sample data, messages logged (masked)" in page.text
    assert page.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in page.headers
    assert _request(app, "GET", "/health").json()["status"] == "ok"
    assert _request(app, "GET", "/webhook/meta").status_code == 403
    assert _request(app, "GET", "/api/tickets").status_code == 401
    response = _request(app, "POST", "/chat", json={"sender": "stage7-test", "text": "refund"})
    assert response.status_code == 200
    assert response.json()["options"] == ["Regular batch", "Refund program batch"]


def test_chat_text_is_not_reflected_and_frontend_uses_text_sinks():
    app = create_app(bot=_Bot(), warmup=False)
    response = _request(app, "POST", "/chat", json={"sender": "xss-test", "text": "<script>alert(1)</script>"})
    assert response.status_code == 200
    assert "<script>" not in response.text
    script = _request(app, "GET", "/app.js").text
    assert "innerHTML" not in script
    assert "textContent" in script


def test_demo_seed_is_separate_flagged_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("ENV", "demo")
    store = Store(tmp_path, secret="test-only-demo-secret")
    assert store.path == tmp_path / "data" / "demo" / "app.db"
    assert store.seed_demo_conversations(DEMO_CONVERSATIONS) == len(DEMO_CONVERSATIONS)
    assert store.seed_demo_conversations(DEMO_CONVERSATIONS) == 0
    with store.connect() as db:
        tickets = [json.loads(row[0]) for row in db.execute("SELECT payload FROM tickets")]
        flags = [row[0] for row in db.execute("SELECT DISTINCT demo FROM messages")]
    assert len(tickets) == len(DEMO_CONVERSATIONS)
    assert 12 <= len(tickets) <= 16
    assert all(ticket["demo"] is True for ticket in tickets)
    assert flags == [1]
