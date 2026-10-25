from __future__ import annotations
import hashlib, hmac, json, os, sqlite3, secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from src.guard import mask_pii

class Store:
    def __init__(self, root: Path, secret: str | None = None):
        self.root = root
        self.path = root / "data/app.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        configured = secret or os.getenv("APP_SECRET", "").strip()
        if not configured:
            configured = secrets.token_urlsafe(32)
            env_file = root / ".env"
            existing = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
            if not any(line.startswith("APP_SECRET=") for line in existing.splitlines()):
                with env_file.open("a", encoding="utf-8", newline="") as stream:
                    if existing and not existing.endswith(("\n", "\r")): stream.write("\n")
                    stream.write(f"APP_SECRET={configured}\n")
            os.environ["APP_SECRET"] = configured
        self.secret = configured.encode()
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sessions(sender_hash TEXT PRIMARY KEY, updated_at TEXT NOT NULL, state TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, sender_hash TEXT NOT NULL, message_id TEXT, role TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tickets(ticket_id TEXT PRIMARY KEY, sender_hash TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS one_open_ticket ON tickets(sender_hash) WHERE status='open';
            CREATE TABLE IF NOT EXISTS kb_gaps(id INTEGER PRIMARY KEY, sender_hash TEXT NOT NULL, query TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS processed_messages(message_id TEXT PRIMARY KEY, sender_hash TEXT NOT NULL, reply_json TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY, sender_hash TEXT NOT NULL, ticket_id TEXT NOT NULL, text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL);
            """)
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db
    def sender_hash(self, sender: str) -> str:
        return hmac.new(self.secret, sender.encode("utf-8"), hashlib.sha256).hexdigest()
    def get_session(self, sender_hash: str, now: datetime) -> dict[str, Any]:
        cutoff = now - timedelta(hours=24)
        with self.connect() as db:
            row = db.execute("SELECT state,updated_at FROM sessions WHERE sender_hash=?", (sender_hash,)).fetchone()
            if not row or datetime.fromisoformat(row["updated_at"]) < cutoff:
                return {"turns": [], "track": None, "verified_learner_id": None, "last_kb_ids": [], "last_intent": None, "pending_options": [], "handed_off": False, "open_ticket_id": None, "clarify_no_match_streak": 0, "last_query_hash": None, "notice_sent": False, "batch_type": None, "pending_refund_batch": False}
            return json.loads(row["state"])
    def save_session(self, sender_hash: str, state: dict[str, Any], now: datetime):
        state["turns"] = state.get("turns", [])[-10:]
        with self.connect() as db:
            db.execute("INSERT INTO sessions VALUES(?,?,?) ON CONFLICT(sender_hash) DO UPDATE SET updated_at=excluded.updated_at,state=excluded.state", (sender_hash, now.isoformat(), json.dumps(state, ensure_ascii=False)))
    def append_message(self, sender_hash: str, message_id: str | None, role: str, text: str, now: datetime):
        with self.connect() as db:
            db.execute("INSERT INTO messages(sender_hash,message_id,role,text,created_at) VALUES(?,?,?,?,?)", (sender_hash, message_id, role, mask_pii(text), now.isoformat()))
    def open_ticket(self, sender_hash: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as db:
            old = db.execute("SELECT payload FROM tickets WHERE sender_hash=? AND status='open'", (sender_hash,)).fetchone()
            if old:
                current = json.loads(old["payload"])
                current["reason_code"] = current["reason_code"] + "," + payload["reason_code"]
                current["last_5_turns"] = payload["last_5_turns"][-5:]
                db.execute("UPDATE tickets SET payload=? WHERE ticket_id=?", (json.dumps(current, ensure_ascii=False), current["ticket_id"]))
                return current
            payload["ticket_id"] = "IS-" + secrets.token_hex(4).upper()
            db.execute("INSERT INTO tickets VALUES(?,?,?,?,?)", (payload["ticket_id"], sender_hash, json.dumps(payload, ensure_ascii=False), "open", payload["created_at"]))
            return payload
    def ticket(self, ticket_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT payload FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
            return json.loads(row["payload"]) if row else None
    def last_customer_message_at(self, ticket_id: str) -> str | None:
        with self.connect() as db:
            row = db.execute("""SELECT m.created_at FROM messages m JOIN tickets t ON t.sender_hash=m.sender_hash
                                WHERE t.ticket_id=? AND m.role='customer' ORDER BY m.created_at DESC LIMIT 1""", (ticket_id,)).fetchone()
            return str(row[0]) if row else None
    def list_tickets(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM tickets ORDER BY created_at")]
    def gap(self, sender_hash: str, query: str, now: datetime):
        with self.connect() as db:
            db.execute("INSERT INTO kb_gaps(sender_hash,query,created_at) VALUES(?,?,?)", (sender_hash, mask_pii(query), now.isoformat()))
    def duplicate(self, message_id: str | None) -> dict[str, Any] | None:
        if not message_id: return None
        with self.connect() as db:
            row = db.execute("SELECT reply_json FROM processed_messages WHERE message_id=?", (message_id,)).fetchone()
            if not row: return None
            try:
                return json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                # A corrupt cached response must not prevent processing the turn again.
                return None
    def processed(self, message_id: str | None, sender_hash: str, reply: dict[str, Any], now: datetime):
        if not message_id: return
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO processed_messages VALUES(?,?,?,?)", (message_id, sender_hash, mask_pii(json.dumps(reply, ensure_ascii=False)), now.isoformat()))
    def append_ticket_message(self, ticket_id: str, text: str):
        with self.connect() as db:
            row = db.execute("SELECT sender_hash,payload FROM tickets WHERE ticket_id=? AND status='open'", (ticket_id,)).fetchone()
            if not row: return
            payload = json.loads(row["payload"])
            payload["last_5_turns"] = (payload.get("last_5_turns", []) + [{"role":"customer","text":mask_pii(text)}])[-5:]
            db.execute("UPDATE tickets SET payload=? WHERE ticket_id=?", (json.dumps(payload, ensure_ascii=False), ticket_id))
            db.execute("INSERT INTO messages(sender_hash,role,text,created_at) VALUES(?,?,?,?)", (row["sender_hash"], "customer", mask_pii(text), datetime.now().astimezone().isoformat()))
    def queue_reply(self, ticket_id: str, text: str):
        with self.connect() as db:
            row = db.execute("SELECT sender_hash FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
            if row: db.execute("INSERT INTO outbox(sender_hash,ticket_id,text,created_at) VALUES(?,?,?,?)", (row[0], ticket_id, mask_pii(text), datetime.now().astimezone().isoformat()))

    def pending_outbox(self, sender_hash: str) -> list[str]:
        with self.connect() as db:
            rows = db.execute("SELECT id,text FROM outbox WHERE sender_hash=? AND status='pending' ORDER BY id", (sender_hash,)).fetchall()
            db.executemany("UPDATE outbox SET status='sent' WHERE id=?", [(row[0],) for row in rows])
            return [row[1] for row in rows]

    def resolve(self, ticket_id: str):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
            if not row: return None
            p = json.loads(row[0]); p["status"] = "resolved"
            db.execute("UPDATE tickets SET status='resolved',payload=? WHERE ticket_id=?", (json.dumps(p), ticket_id))
            return p
