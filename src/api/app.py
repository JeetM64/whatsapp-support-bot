from __future__ import annotations

import hashlib, hmac, html, json, os, secrets, time, uuid
import logging
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import parse_qsl

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import yaml

from src.api.channels import FakeChannel, MetaChannel
from src.app.bot import Bot
from src.app.store import Store
from src.rag.config import load_dotenv
from src.rag.engine import RagEngine
from src.rag.providers import NoneProvider

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT)
STARTED = time.monotonic()
MAX_BODY = 64 * 1024
LOGGER = logging.getLogger("customer_support.api")


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    sender: str = Field(min_length=1, max_length=100)
    message_id: str | None = Field(default=None, max_length=200)


class AgentAuthIn(BaseModel):
    key: str = Field(min_length=1, max_length=512)


def check_twilio(url: str, params: dict[str,str], signature: str, token: str) -> bool:
    canonical = url + "".join(k + params[k] for k in sorted(params))
    digest = hmac.new(token.encode(), canonical.encode(), hashlib.sha1).digest()
    import base64
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature)


def create_app(*, bot: Bot | None = None, channel=None, warmup: bool = True) -> FastAPI:
    api = FastAPI(title="Internship Studio Support API", version="1.0.0")
    default_channel = FakeChannel() if (os.getenv("ENV") or "dev").casefold() == "dev" else MetaChannel()
    state = {"bot": bot, "channel": channel or default_channel, "seen": set(), "limits": defaultdict(deque), "warmup": warmup}
    api.state.services = state
    try:
        facts_doc = yaml.safe_load((ROOT / "kb" / "verified_facts.yaml").read_text(encoding="utf-8-sig")) or {}
        home_link = facts_doc.get("verified_facts", {}).get("placeholders", {}).get("HELP_HOME_URL", {}).get("value", "")
    except (OSError, yaml.YAMLError, AttributeError):
        home_link = ""
    origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if x.strip()]

    from fastapi.middleware.cors import CORSMiddleware
    api.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-Request-ID"])

    @api.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_BODY:
            return JSONResponse(status_code=413, content={"error":"request_too_large", "request_id":request.state.request_id})
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        return response

    @api.on_event("startup")
    async def startup():
        if state["bot"] is None:
            state["bot"] = Bot(ROOT, engine=RagEngine(ROOT, provider=NoneProvider()))
        if (os.getenv("ENV") or "dev").casefold() == "demo":
            store = state["bot"].store
            with store.connect() as db:
                ticket_count = db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            if ticket_count == 0:
                from src.app.demo_seed import DEMO_CONVERSATIONS
                store.seed_demo_conversations(DEMO_CONVERSATIONS)
        if state["warmup"]:
            try: state["bot"].engine.retriever
            except Exception: pass

    def services():
        if state["bot"] is None:
            state["bot"] = Bot(ROOT, engine=RagEngine(ROOT, provider=NoneProvider()))
        return state["bot"]

    def limited(key: str, max_requests: int = 30, window: int = 60) -> bool:
        now = time.monotonic(); q = state["limits"][key]
        while q and now - q[0] > window: q.popleft()
        if len(q) >= max_requests: return True
        q.append(now); return False

    async def body_bytes(request: Request) -> bytes:
        data = await request.body()
        if len(data) > MAX_BODY: raise HTTPException(413, "request_too_large")
        return data

    @api.exception_handler(Exception)
    async def generic_error(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"error":"internal_error", "request_id":getattr(request.state,"request_id","")})

    @api.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error":"invalid_request", "request_id":getattr(request.state,"request_id","")})

    @api.get("/health")
    async def health():
        b = services(); retriever = b.engine.retriever
        cfg = b.engine.config
        return {"status":"ok", "kb_hash":getattr(retriever,"kb_hash",None) or getattr(retriever,"content_hash",None) or getattr(cfg,"kb_hash",None),
                "model":getattr(cfg,"embedding_model",None), "provider":getattr(getattr(b.engine,"provider",None),"name","none"),
                "degraded":bool(getattr(b.engine,"_init_error",None) or getattr(b.engine,"retriever",None) is None), "uptime_seconds":round(time.monotonic()-STARTED,2)}

    @api.post("/chat")
    async def chat(payload: ChatIn, request: Request):
        ip = request.client.host if request.client else "unknown"
        sender = "web:" + payload.sender
        if limited("ip:"+ip) or limited("sender:"+sender, 12): raise HTTPException(429,"rate_limited")
        bot = services()
        result = bot.handle_message(sender, payload.text, payload.message_id or request.headers.get("x-message-id"), "web")
        debug = dict(getattr(result, "debug", {}) or {})
        decision = str(debug.get("rag_decision") or debug.get("decision") or "UNKNOWN").upper()
        reason_code = debug.get("reason_code") or debug.get("reason") or "unknown"
        options = list(debug.get("options") or []) if decision == "CLARIFY" else []
        related = list(debug.get("related") or [])
        selected_entry = {}
        try:
            entries = bot.engine.retriever.entries
            if decision in {"ANSWER", "CLARIFY"}:
                selected_entry = next(
                    (entries[key] for key in debug.get("kb_ids", []) if key in entries),
                    {},
                )
        except (AttributeError, KeyError, TypeError):
            selected_entry = {}
        source_status = selected_entry.get("source_status")
        if source_status not in {"verified", "partly_verified", "pending"}:
            source_status = "pending" if (
                not selected_entry
                or selected_entry.get("is_mock", False)
                or decision in {"NO_MATCH", "CLARIFY"}
            ) else "verified"
        help_link = selected_entry.get("help_link") or home_link
        if decision == "CLARIFY" and not options:
            if reason_code == "refund_batch_type":
                options = ["Regular batch", "Refund program batch"]
            else:
                try:
                    entries = bot.engine.retriever.entries
                    options = [entries[key].get("question", key) for key in debug.get("kb_ids", []) if key in entries][:3]
                except Exception:
                    options = []
        debug.update({
            "decision": decision,
            "reason_code": reason_code,
            "kb_ids": debug.get("kb_ids", []),
            "confidence": debug.get("confidence", 0),
            "mode": debug.get("mode", "fallback"),
            "source_status": source_status,
            "help_link": help_link,
        })
        return {"messages":result.messages, "ticket":result.ticket, "request_id":request.state.request_id,
                "options":options, "related":related, "source_status":source_status, "help_link":help_link, "debug":debug}

    @api.get("/webhook/meta")
    async def meta_verify(request: Request):
        p = request.query_params
        verify_token = os.getenv("META_VERIFY_TOKEN", "")
        if verify_token and p.get("hub.mode") == "subscribe" and hmac.compare_digest(p.get("hub.verify_token", ""), verify_token):
            return Response(p.get("hub.challenge", ""), media_type="text/plain")
        raise HTTPException(403,"verification_failed")

    def process_meta(payload: dict):
        b = services()
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    mid, sender = msg.get("id"), msg.get("from")
                    if not mid or not sender or mid in state["seen"]: continue
                    state["seen"].add(mid)
                    if b.store.duplicate(mid): continue
                    if limited("sender:meta:" + hashlib.sha256(sender.encode()).hexdigest(), 12): continue
                    text = msg.get("text", {}).get("body")
                    if msg.get("type") != "text" or not text:
                        text = "I can help with text messages. Please send your question as text."
                    normalized_sender = "whatsapp:" + "".join(ch for ch in sender if ch.isdigit())
                    reply = b.handle_message(normalized_sender, text, mid, "meta")
                    for answer in reply.messages:
                        for start in range(0, len(answer), 600): state["channel"].send(sender, answer[start:start+600])

    @api.post("/webhook/meta")
    async def meta_webhook(request: Request, background: BackgroundTasks):
        ip = request.client.host if request.client else "unknown"
        if limited("ip:meta:" + ip, 120): raise HTTPException(429,"rate_limited")
        raw = await body_bytes(request)
        signature = request.headers.get("x-hub-signature-256", "")
        secret = os.getenv("META_APP_SECRET", "")
        if (os.getenv("ENV") or "dev").casefold() == "dev" and not secret:
            LOGGER.warning("Meta signature verification skipped because ENV=dev and no app secret is configured")
            pass  # Local development may omit signature verification; production never may.
        else:
            expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
            if not secret or not hmac.compare_digest(signature, expected): raise HTTPException(403,"invalid_signature")
        try: payload = json.loads(raw)
        except (ValueError, UnicodeDecodeError): raise HTTPException(400,"invalid_json")
        # A non-text webhook is acknowledged, then converted to a safe text-only response.
        background.add_task(process_meta, payload)
        return {"status":"accepted", "request_id":request.state.request_id}

    @api.post("/webhook/twilio")
    async def twilio_webhook(request: Request):
        ip = request.client.host if request.client else "unknown"
        if limited("ip:twilio:" + ip, 120): raise HTTPException(429,"rate_limited")
        raw = await body_bytes(request)
        params = dict(parse_qsl(raw.decode("utf-8", errors="replace"), keep_blank_values=True))
        token = os.getenv("TWILIO_AUTH_TOKEN", "")
        url = str(request.url)
        if not ((os.getenv("ENV") or "dev").casefold() == "dev" and not token):
            if not token or not check_twilio(url, params, request.headers.get("x-twilio-signature", ""), token):
                raise HTTPException(403,"invalid_signature")
        else:
            LOGGER.warning("Twilio signature verification skipped because ENV=dev and no auth token is configured")
        sender, text, mid = params.get("From", ""), params.get("Body", ""), params.get("MessageSid", "")
        if not sender: raise HTTPException(400,"invalid_message")
        if mid and services().store.duplicate(mid):
            return Response("<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response/>", media_type="application/xml")
        if limited("sender:twilio:"+hashlib.sha256(sender.encode()).hexdigest(), 12): raise HTTPException(429,"rate_limited")
        normalized_sender = "whatsapp:" + "".join(ch for ch in sender if ch.isdigit())
        result = services().handle_message(normalized_sender, text or "Please send your question as text.", mid, "twilio")
        body = "".join(f"<Message>{html.escape(part)}</Message>" for msg in result.messages for part in (msg[i:i+600] for i in range(0,len(msg),600)))
        return Response(f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response>{body}</Response>", media_type="application/xml")

    def authorize(authorization: str | None):
        key = os.getenv("AGENT_API_KEY", "")
        if not key or not authorization or not authorization.startswith("Bearer ") or not hmac.compare_digest(authorization[7:], key):
            raise HTTPException(401,"unauthorized")

    @api.post("/api/agent/auth")
    async def agent_auth(payload: AgentAuthIn, request: Request):
        ip = request.client.host if request.client else "unknown"
        queue = state["limits"]["agent-auth-fail:" + ip]
        now = time.monotonic()
        while queue and now - queue[0] > 300:
            queue.popleft()
        if len(queue) >= 10:
            raise HTTPException(429, "too_many_attempts")
        configured = os.getenv("AGENT_API_KEY", "")
        valid = bool(configured) and hmac.compare_digest(payload.key, configured)
        if not valid:
            queue.append(now)
            raise HTTPException(401, "unauthorized")
        queue.clear()
        return {"authenticated": True}

    @api.get("/api/tickets")
    async def tickets(authorization: str | None = Header(default=None)):
        authorize(authorization); return services().store.list_tickets()

    @api.get("/api/tickets/{ticket_id}")
    async def ticket(ticket_id: str, authorization: str | None = Header(default=None)):
        authorize(authorization); item = services().store.ticket(ticket_id)
        if not item: raise HTTPException(404,"not_found")
        return item

    @api.post("/api/tickets/{ticket_id}/reply")
    async def reply(ticket_id: str, payload: dict, authorization: str | None = Header(default=None)):
        authorize(authorization); item = services().store.ticket(ticket_id)
        if not item: raise HTTPException(404,"not_found")
        text = str(payload.get("text", ""))[:600]
        if not text: raise HTTPException(422,"text_required")
        # Customer replies after the WhatsApp 24-hour window require an approved template.
        from datetime import datetime, timezone
        created = datetime.fromisoformat(services().store.last_customer_message_at(ticket_id) or item["created_at"])
        needs_template = (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds() > 86400
        services().store.queue_reply(ticket_id, text)
        return {"queued":True,"needs_template":needs_template}

    @api.post("/api/tickets/{ticket_id}/resolve")
    async def resolve(ticket_id: str, authorization: str | None = Header(default=None)):
        authorize(authorization); result = services().store.resolve(ticket_id)
        if not result: raise HTTPException(404,"not_found")
        return result

    @api.get("/api/metrics")
    async def metrics(authorization: str | None = Header(default=None)):
        authorize(authorization)
        db = services().store.connect()
        try:
            tickets = [json.loads(row[0]) for row in db.execute("SELECT payload FROM tickets")]
            ticket_senders = {row[0] for row in db.execute("SELECT sender_hash FROM tickets")}
            messages = [dict(row) for row in db.execute("SELECT sender_hash,role,created_at,text FROM messages ORDER BY created_at")]
            gaps = db.execute("SELECT COUNT(*) FROM kb_gaps").fetchone()[0]
            sessions = [json.loads(row[0]) for row in db.execute("SELECT state FROM sessions")]
        finally: db.close()
        from collections import Counter
        reasons = Counter(t.get("reason_code", "unknown") for t in tickets)
        priorities = Counter(t.get("priority", "unknown") for t in tickets)
        intents = Counter(t.get("intent", "unknown") for t in tickets)
        languages = Counter(t.get("language", "unknown") for t in tickets)
        response_latencies=[]; previous={}
        for msg in messages:
            created = __import__('datetime').datetime.fromisoformat(msg["created_at"])
            if msg["role"] == "customer": previous[msg["sender_hash"]] = created
            elif msg["role"] == "assistant" and msg["sender_hash"] in previous:
                response_latencies.append(max(0,(created-previous.pop(msg["sender_hash"])).total_seconds()*1000))
        languages=Counter()
        from src.rag.normalize import detect_language
        for msg in messages:
            if msg["role"] == "customer": languages[detect_language(msg["text"])] += 1
        batch_types=Counter(s.get("batch_type") or "unknown" for s in sessions)
        from datetime import datetime, timezone
        now=datetime.now(timezone.utc); breaches=0
        for t in tickets:
            if t.get("status") == "open" and t.get("sla_deadline"):
                try:
                    from zoneinfo import ZoneInfo
                    deadline=datetime.strptime(t["sla_deadline"], "%a %d %b, %I:%M %p IST").replace(year=now.astimezone(ZoneInfo("Asia/Kolkata")).year,tzinfo=ZoneInfo("Asia/Kolkata"))
                    breaches += int(deadline < now)
                except ValueError: pass
        customer_count=sum(m["role"]=="customer" for m in messages)
        open_sender_count=len({m["sender_hash"] for m in messages if m["role"]=="customer" and m["sender_hash"] in ticket_senders})
        return {"handled_messages":customer_count,"auto_resolved_percent":0 if not customer_count else round(100*max(0,customer_count-open_sender_count)/customer_count,1),
                "escalations_by_reason":dict(reasons),"escalation_percent_by_reason":{k:round(v*100/max(len(tickets),1),1) for k,v in reasons.items()},
                "escalations_by_priority":dict(priorities),"escalation_percent_by_priority":{k:round(v*100/max(len(tickets),1),1) for k,v in priorities.items()},
                "average_latency_ms":None if not response_latencies else round(sum(response_latencies)/len(response_latencies),1),
                "top_intents":dict(intents.most_common(10)),"kb_gaps":gaps,"sla_breaches":breaches,
                "language_split":dict(languages),"batch_type_split":dict(batch_types)}

    @api.get("/api/metrics/public")
    async def public_metrics():
        store = services().store
        db = store.connect()
        try:
            tickets = [json.loads(row[0]) for row in db.execute("SELECT payload FROM tickets")]
            messages = [tuple(row) for row in db.execute("SELECT sender_hash,role,created_at,text FROM messages ORDER BY created_at")]
            sessions = [json.loads(row[0]) for row in db.execute("SELECT state FROM sessions")]
            gap_queries = [str(row[0]) for row in db.execute("SELECT query FROM kb_gaps")]
            usage_rows = [tuple(row) for row in db.execute("SELECT mode,input_tokens,output_tokens,cost_usd FROM token_usage")]
            response_rows = [tuple(row) for row in db.execute("SELECT latency_ms,auto_resolved FROM response_metrics")]
        finally:
            db.close()

        from collections import Counter
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        reasons = Counter(str(ticket.get("reason_code", "unknown")) for ticket in tickets)
        priorities = Counter(str(ticket.get("priority", "unknown")) for ticket in tickets)
        intents = Counter(str(ticket.get("intent", "unknown")) for ticket in tickets)
        message_count = sum(role == "customer" for _, role, _, _ in messages)
        language_counts = Counter()
        from src.rag.normalize import detect_language
        for _, role, _, text in messages:
            if role == "customer":
                language_counts[detect_language(text)] += 1
        batch_counts = Counter(str(session.get("batch_type") or "unknown") for session in sessions)

        # Map stored gap queries to a small, fixed topic vocabulary; never expose a query.
        gap_topics = Counter()
        for query in gap_queries:
            folded = query.casefold()
            if any(term in folded for term in ("college", "campus", "partnership", "tpo")):
                topic = "college partnerships"
            elif any(term in folded for term in ("refund", "cancel", "money back")):
                topic = "refund terms"
            elif any(term in folded for term in ("fee", "price", "payment", "receipt")):
                topic = "fees and payments"
            elif any(term in folded for term in ("certificate", "approval", "aicte", "ugc", "nsdc")):
                topic = "certificates and approvals"
            else:
                topic = "other information"
            gap_topics[topic] += 1

        now = datetime.now(timezone.utc)
        local_year = now.astimezone(ZoneInfo("Asia/Kolkata")).year
        breaches = 0
        for ticket in tickets:
            if ticket.get("status") != "open" or not ticket.get("sla_deadline"):
                continue
            try:
                deadline = datetime.strptime(ticket["sla_deadline"], "%a %d %b, %I:%M %p IST").replace(
                    year=local_year, tzinfo=ZoneInfo("Asia/Kolkata")
                )
                if deadline - now.astimezone(ZoneInfo("Asia/Kolkata")) > __import__("datetime").timedelta(days=300):
                    deadline = deadline.replace(year=local_year - 1)
                breaches += int(deadline < now.astimezone(ZoneInfo("Asia/Kolkata")))
            except (ValueError, TypeError):
                continue

        provider_name = str(getattr(getattr(services().engine, "provider", None), "name", "none")).casefold()
        numeric_costs = [float(cost) for _, _, _, cost in usage_rows if cost is not None]
        if provider_name in {"none", "null", "no_llm"}:
            cost_per_thousand, cost_status = 0.0, "no_llm_mode"
        elif numeric_costs and message_count:
            cost_per_thousand, cost_status = round(sum(numeric_costs) * 1000 / message_count, 6), "token_logs"
        else:
            cost_per_thousand, cost_status = None, "token_logs_unavailable"

        denominator = len(tickets) or 1
        return {
            "demo_data": (os.getenv("ENV") or "dev").casefold() == "demo",
            "messages_handled": message_count,
            "auto_resolved_percent": None if not response_rows else round(100 * sum(int(row[1]) for row in response_rows) / len(response_rows), 1),
            "escalations_by_reason": [{"label": key, "count": value, "rate_percent": round(value * 100 / denominator, 1)} for key, value in reasons.most_common()],
            "escalations_by_priority": [{"label": key, "count": value, "rate_percent": round(value * 100 / denominator, 1)} for key, value in priorities.most_common()],
            "average_bot_latency_ms": None if not response_rows else round(sum(float(row[0]) for row in response_rows) / len(response_rows), 1),
            "top_intents": [{"label": key, "count": value} for key, value in intents.most_common(10)],
            "kb_gaps": [{"topic": key, "count": value} for key, value in gap_topics.most_common()],
            "language_split": dict(language_counts),
            "batch_type_split": dict(batch_counts),
            "sla_breaches": breaches,
            "token_cost_per_1000_messages_usd": cost_per_thousand,
            "token_cost_status": cost_status,
        }

    frontend = ROOT / "frontend"
    if frontend.is_dir():
        @api.get("/agent", include_in_schema=False)
        async def agent_page():
            return FileResponse(frontend / "agent.html")

        @api.get("/founder", include_in_schema=False)
        async def founder_page():
            return FileResponse(frontend / "founder.html")
        # Registered last: concrete API, health, and webhook routes keep precedence.
        api.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return api


app = create_app()
