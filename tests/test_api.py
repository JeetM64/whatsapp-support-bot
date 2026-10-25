from __future__ import annotations

import asyncio, base64, hashlib, hmac, json
import sqlite3
from datetime import datetime, timezone, timedelta
import pytest
import httpx

fastapi = pytest.importorskip("fastapi")

from src.api.app import create_app, check_twilio
from src.api.channels import FakeChannel


class LocalASGIClient:
    """Synchronous test facade over ASGITransport; avoids the host's stuck AnyIO portal."""
    def __init__(self, app):
        self.app=app
        self.transport=httpx.ASGITransport(app=app)
    def request(self, method, url, **kwargs):
        async def send():
            async with httpx.AsyncClient(transport=self.transport,base_url="http://testserver") as client:
                return await client.request(method,url,**kwargs)
        return asyncio.run(send())
    def get(self,url,**kwargs): return self.request("GET",url,**kwargs)
    def post(self,url,**kwargs): return self.request("POST",url,**kwargs)


class StubStore:
    def __init__(self):
        self.messages=[]; self.tickets={}; self.gaps=0; self.replies=[]; self.seen=set()
    def duplicate(self, mid): return {"messages":["cached"]} if mid in self.seen else None
    def list_tickets(self): return list(self.tickets.values())
    def ticket(self, ticket_id): return self.tickets.get(ticket_id)
    def last_customer_message_at(self, ticket_id):
        return next((msg[2] for msg in reversed(self.messages) if msg[1]=="customer"),None)
    def resolve(self, ticket_id):
        item=self.tickets.get(ticket_id)
        if item: item["status"]="resolved"
        return item
    def queue_reply(self, ticket_id, text): self.replies.append((ticket_id,text))
    def connect(self):
        db=sqlite3.connect(":memory:"); db.row_factory=sqlite3.Row
        db.executescript("CREATE TABLE tickets(payload TEXT,sender_hash TEXT); CREATE TABLE messages(sender_hash TEXT,role TEXT,created_at TEXT,text TEXT); CREATE TABLE kb_gaps(id INTEGER); CREATE TABLE sessions(state TEXT);")
        for item in self.tickets.values(): db.execute("INSERT INTO tickets VALUES(?,?)",(json.dumps(item),"hash1"))
        for msg in self.messages: db.execute("INSERT INTO messages VALUES(?,?,?,?)",msg)
        db.execute("INSERT INTO kb_gaps VALUES(1)",) if self.gaps else None
        return db


class StubBot:
    engine = type("Engine", (), {"retriever":type("Retriever", (), {"kb_hash":"test-hash"})(), "config":type("Config", (), {"embedding_model":"test-model"})(), "provider":type("Provider", (), {"name":"none"})()})()
    def __init__(self): self.store=StubStore(); self.calls=[]
    def handle_message(self, sender, text, message_id, channel):
        self.calls.append((sender,text,message_id,channel))
        if message_id: self.store.seen.add(message_id)
        messages=["x"*1300] if text=="long reply trigger" else ["ok"]
        return type("Reply", (), {"messages":messages,"ticket":None})()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("AGENT_API_KEY", "test-key")
    monkeypatch.setenv("META_VERIFY_TOKEN", "verify")
    return LocalASGIClient(create_app(bot=StubBot(), channel=FakeChannel(), warmup=False))


def test_health_and_web_chat_and_length_limit(client):
    assert client.get("/health").status_code == 200
    assert client.post("/chat", json={"sender":"s1","text":"hello"}).json()["messages"] == ["ok"]
    assert client.post("/chat", content=b" " * 65537, headers={"content-type":"application/json"}).status_code == 413


def test_meta_verification_signature_and_dedupe(client, monkeypatch):
    assert client.get("/webhook/meta", params={"hub.mode":"subscribe","hub.verify_token":"verify","hub.challenge":"123"}).text == "123"
    monkeypatch.setenv("META_APP_SECRET", "secret")
    raw = json.dumps({"entry":[{"changes":[{"value":{"statuses":[{"id":"ignore"}],"messages":[{"id":"wamid-1","from":"919000000001","type":"text","text":{"body":"hello"}}]}}]}]}).encode()
    sig = "sha256=" + hmac.new(b"secret", raw, hashlib.sha256).hexdigest()
    assert client.post("/webhook/meta", content=raw, headers={"x-hub-signature-256":sig}).status_code == 200
    assert client.app.state.services["channel"].sent == [("919000000001","ok")]
    assert client.post("/webhook/meta", content=raw, headers={"x-hub-signature-256":sig}).status_code == 200
    assert len(client.app.state.services["channel"].sent) == 1
    assert client.post("/webhook/meta", content=raw, headers={"x-hub-signature-256":"sha256=bad"}).status_code == 403


def test_meta_requires_signature_outside_dev(client, monkeypatch):
    monkeypatch.setenv("ENV","production"); monkeypatch.setenv("META_APP_SECRET","secret")
    raw=b'{"entry":[]}'
    assert client.post("/webhook/meta",content=raw).status_code==403


def test_twilio_signature_exact_canonical_form():
    params={"Body":"Hi","From":"whatsapp:+919000000001"}; token="secret"; url="https://example.test/webhooks/twilio"
    value=url+"BodyHiFromwhatsapp:+919000000001"
    sig=base64.b64encode(hmac.new(token.encode(),value.encode(),hashlib.sha1).digest()).decode()
    assert check_twilio(url,params,sig,token)
    assert not check_twilio(url,params,"wrong",token)


def test_agent_api_requires_bearer_key(client):
    assert client.get("/api/tickets").status_code == 401
    assert client.get("/api/tickets",headers={"Authorization":"Bearer test-key"}).status_code == 200


def test_agent_reply_template_rule_and_resolve(client):
    store=client.app.state.services["bot"].store
    old=(datetime.now(timezone.utc)-timedelta(hours=25)).isoformat()
    store.tickets["IS-OLD"]={"ticket_id":"IS-OLD","created_at":old,"status":"open","reason_code":"human_request","priority":"P3"}
    headers={"Authorization":"Bearer test-key"}
    reply=client.post("/api/tickets/IS-OLD/reply",json={"text":"We received your request"},headers=headers)
    assert reply.json()=={"queued":True,"needs_template":True}
    assert client.get("/api/tickets/IS-OLD",headers=headers).status_code==200
    assert client.post("/api/tickets/IS-OLD/resolve",headers=headers).json()["status"]=="resolved"


def test_metrics_are_derived_from_database_rows(client):
    store=client.app.state.services["bot"].store
    store.messages.extend([
        ("hashed-sender","customer",datetime.now(timezone.utc).isoformat(),"hello"),
        ("hashed-sender","assistant",datetime.now(timezone.utc).isoformat(),"reply"),
    ])
    store.gaps=1
    response=client.get("/api/metrics",headers={"Authorization":"Bearer test-key"})
    assert response.status_code==200
    assert response.json()["handled_messages"]==1
    assert response.json()["kb_gaps"]==1
    assert response.json()["average_latency_ms"] is not None


def test_twilio_text_reply_and_non_text_fallback(client):
    params={"From":"whatsapp:+919000000001","Body":"Hello","MessageSid":"SM1"}
    response=client.post("/webhook/twilio",data=params)
    assert response.status_code==200 and "<Message>ok</Message>" in response.text
    duplicate=client.post("/webhook/twilio",data=params)
    assert "<Response/>" in duplicate.text


def test_cors_request_id_and_rate_limit(client):
    response=client.post("/chat",json={"sender":"same","text":"hi"},headers={"origin":"http://localhost:3000"})
    assert response.headers["access-control-allow-origin"]=="http://localhost:3000"
    assert response.headers["x-request-id"]
    for _ in range(12): client.post("/chat",json={"sender":"burst","text":"hi"})
    assert client.post("/chat",json={"sender":"burst","text":"hi"}).status_code==429
