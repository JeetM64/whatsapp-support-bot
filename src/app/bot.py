from __future__ import annotations
import json, re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any
from src.guard import GuardRules, mask_pii
from .store import Store
from src.guard.l1 import L1Classifier, merge_l1
from src.rag.normalize import detect_language

IST = ZoneInfo("Asia/Kolkata")

@dataclass
class BotReply:
    messages: list[str]
    ticket: dict[str, Any] | None = None
    debug: dict[str, Any] = field(default_factory=dict)


def _local_now(value: datetime | None) -> datetime:
    if value is None: return datetime.now(IST)
    return value.replace(tzinfo=IST) if value.tzinfo is None else value.astimezone(IST)

def _next_open(t: datetime) -> datetime:
    t = t.astimezone(IST)
    while t.weekday() == 6:
        t = (t + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    if t.hour < 10: return t.replace(hour=10, minute=0, second=0, microsecond=0)
    if t.hour >= 19 or t.weekday() == 6:
        t = (t + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        while t.weekday() == 6: t += timedelta(days=1)
    return t

def sla_deadline(now: datetime, priority: str, hours: int) -> datetime:
    t = _next_open(now)
    remaining = float(hours)
    while remaining > 0:
        t = _next_open(t)
        close = t.replace(hour=19, minute=0, second=0, microsecond=0)
        available = (close - t).total_seconds() / 3600
        if remaining <= available: return t + timedelta(hours=remaining)
        remaining -= available
        t = close + timedelta(seconds=1)
    return t

class Bot:
    def __init__(self, root: Path, engine=None, store: Store | None = None):
        self.root = root.resolve()
        self.engine = engine
        self.store = store or Store(self.root)
        self.guard = GuardRules(self.root)
        config = json.loads(json.dumps({}))
        import yaml
        self.hours = yaml.safe_load((self.root / "config/escalation_rules.yaml").read_text(encoding="utf-8"))
        self.messages = yaml.safe_load((self.root / "config/messages.yaml").read_text(encoding="utf-8"))
        self.demo_mode = self._rag_config_demo()
        self.learners = json.loads((self.root / "data/mock_learners.json").read_text(encoding="utf-8"))

    def _rag_config_demo(self):
        try:
            import yaml
            data = yaml.safe_load((self.root / "config/rag.yaml").read_text(encoding="utf-8"))
            return bool(data.get("demo_mode", True))
        except Exception: return True

    def _eta(self, now: datetime, priority: str) -> str:
        hrs = int(self.hours.get("sla_hours", {}).get(priority, 24))
        deadline = sla_deadline(now, priority, hrs)
        return deadline.strftime("%a %d %b, %I:%M %p IST")

    def _ticket(self, sender_hash, now, text, result, guard_result, turns):
        priority = guard_result.priority or "P3"
        reason = guard_result.reason_code or "high_risk_unmatched"
        intent = guard_result.reason_code or result.reason_code
        lang = result.language if result else "English"
        sample = self.messages["escalation"][lang.casefold() if lang.casefold() in {"english", "hinglish"} else "english"]
        payload = {
            "ticket_id": "", "reason_code": reason, "priority": priority,
            "customer_masked_id": sender_hash[:12], "language": lang,
            "sentiment": "angry" if priority == "P2" else "neutral", "intent": intent,
            "summary_3_lines": [f"Reason: {reason}", f"Customer: {mask_pii(text)[:180]}", f"KB entries tried: {', '.join([e.id for e in result.entries]) if result else 'none'}"],
            "last_5_turns": turns[-5:], "kb_ids_tried": [e.id for e in result.entries] if result else [],
            "confidence": float(result.confidence if result else 0),
            "suggested_reply": sample["suggested_reply"], "sla_deadline": self._eta(now, priority),
            "created_at": now.isoformat(), "status": "open"
        }
        return self.store.open_ticket(sender_hash, payload)

    def handle_message(self, sender: str, text: str, message_id: str | None, channel: str,
                       now: datetime | None = None) -> BotReply:
        when = _local_now(now)
        raw_text = str(text or "")[:600]
        clean = mask_pii(raw_text)
        sender_hash = self.store.sender_hash(sender)
        try:
            duplicate = self.store.duplicate(message_id)
            if channel == "system": return BotReply([""])
            if duplicate: return BotReply(**duplicate)
            state = self.store.get_session(sender_hash, when)
            queued_messages = self.store.pending_outbox(sender_hash)
            self.store.append_message(sender_hash, message_id, "customer", raw_text, when)
            state.setdefault("turns", []).append({"role":"customer", "text":clean})
            state["turns"] = state["turns"][-10:]
            if state.get("handed_off"):
                open_ticket = self.store.ticket(state.get("open_ticket_id", ""))
                if open_ticket and open_ticket.get("status") == "open":
                    self.store.append_ticket_message(open_ticket["ticket_id"], clean)
                    human_messages = queued_messages
                    if raw_text.strip().casefold() in {"status", "ticket status"}:
                        out = human_messages + [f"Your ticket {open_ticket['ticket_id']} is open. Current ETA: {open_ticket['sla_deadline']}."]
                    else:
                        out = human_messages
                    result = BotReply(out, open_ticket, {"decision":"HANDOFF","reason":"ticket_open","priority":open_ticket.get("priority"),"kb_ids":[]})
                    self.store.save_session(sender_hash, state, when); self.store.processed(message_id, sender_hash, result.__dict__, when)
                    return result
                state["handed_off"] = False
                state["open_ticket_id"] = None            # Handle CLARIFY selection and terse follow-up against stored options/KB id.
            follow = raw_text.strip().casefold()
            if state.get("pending_options") and re.match(r"^(1|2|3|one|two|three|payment wala|certificate wala)$", follow):
                options = state["pending_options"]
                idx = 0 if follow in {"1","one","payment wala"} else 1
                if idx < len(options): raw_text = f"{raw_text} {options[idx]}"
            elif len(follow.split()) <= 4 and state.get("last_kb_ids"):
                prior_id = state["last_kb_ids"][0]
                prior = self.engine.retriever.entries.get(prior_id, {}) if self.engine else {}
                raw_text = f"{raw_text} about {prior.get('question', prior_id)}"
            else:
                raw_text = clean
            same_query = state.get("last_query_hash") == __import__("hashlib").sha256(clean.casefold().encode()).hexdigest()
            # L0 runs first; deterministic RAG is called only if no hard rule fires.
            guess = self.guard.classify(clean, frustration_loop=state.get("clarify_no_match_streak",0) >= 2 or same_query,
                                        status_authorized=self._identity_ok(sender))
            rag = None
            if self.engine and guess.action == "continue":
                from concurrent.futures import ThreadPoolExecutor
                from types import SimpleNamespace
                l1_classifier = L1Classifier()
                l1_pool = ThreadPoolExecutor(max_workers=2)
                l1_future = l1_pool.submit(l1_classifier.classify, clean, self.engine.provider, 2.0)
                retrieval_future = l1_pool.submit(self.engine.retriever.retrieve, clean)
                try:
                    l1 = l1_future.result(timeout=2.0)
                except Exception:
                    l1 = l1_classifier.classify(clean)
                finally:
                    l1_pool.shutdown(wait=False, cancel_futures=True)
                if merge_l1(False, l1):
                    from src.guard import GuardResult
                    guess = GuardResult("l1_needs_human", "P3", "escalate")
                    rag = SimpleNamespace(language=detect_language(clean), confidence=0.0, entries=[], reason_code="l1_needs_human")
                else:
                    try: retrieval_future.result(timeout=0.1)
                    except Exception: pass
                    rag = self.engine.answer(raw_text)
            elif self.engine and guess.action in {"kb_first_aid_ticket", "offer_human"}:
                if guess.action == "kb_first_aid_ticket":
                    rag = self.engine.answer(raw_text, force_extractive=True)
                else:
                    rag = self.engine.answer(raw_text, force_extractive=True)
            if rag and rag.decision.value == "NO_MATCH" and guess.action in {"continue", "offer_human"} and self.guard.matches("R5", clean):
                guess = self.guard.classify(clean, unmatched_high_risk=True, status_authorized=self._identity_ok(sender))
            if guess.action == "continue" and rag and rag.decision.value == "NO_MATCH":
                top_entry = self.engine.retriever.entries.get(rag.entries[0].id, {}) if self.engine and rag.entries else {}
                high_risk_kb = bool(top_entry.get("escalate_if_unmatched")) or top_entry.get("risk_level") == "high"
                if high_risk_kb:
                    guess = self.guard.classify(clean, unmatched_high_risk=True, status_authorized=self._identity_ok(sender))
                self.store.gap(sender_hash, clean, when)
            if rag and rag.decision.value == "CLARIFY" and self.engine:
                state["pending_options"] = [self.engine.retriever.entries[e.id].get("question", e.id) for e in rag.entries if e.id in self.engine.retriever.entries][:3]
            if guess.action == "continue" and rag and rag.decision.value in {"CLARIFY", "NO_MATCH"} and state.get("clarify_no_match_streak", 0) >= 1:
                from src.guard import GuardResult
                guess = GuardResult("frustration_loop", "P3", "escalate")
            if guess.action == "continue" and rag and rag.decision.value in {"CLARIFY", "NO_MATCH"}:
                state["clarify_no_match_streak"] = int(state.get("clarify_no_match_streak",0)) + 1
            elif guess.action == "continue": state["clarify_no_match_streak"] = 0
            if guess.action == "warn":
                if state.get("sensitive_warned"):
                    out = ["Sensitive information was masked. Please do not share it here."]
                else:
                    out = [self.messages["sensitive_data"]["english"]]
                    state["sensitive_warned"] = True
            elif guess.action == "support":
                reply_text = self.messages["distress"]["english"]
                ticket = self._ticket(sender_hash, when, clean, rag, guess, state["turns"])
                out = [reply_text + " " + self._escalation_message(ticket, rag.language if rag else "English", when)]
                state.update(handed_off=True, open_ticket_id=ticket["ticket_id"])
            elif guess.action in {"escalate", "kb_first_aid_ticket"}:
                ticket = self._ticket(sender_hash, when, clean, rag, guess, state["turns"])
                base = rag.reply if guess.action == "kb_first_aid_ticket" and rag else ""
                escalation = self._escalation_message(ticket, rag.language if rag else "English", when)
                out = ([base] if base else []) + [escalation]
                state.update(handed_off=True, open_ticket_id=ticket["ticket_id"])
            elif guess.action == "offer_human":
                out = [rag.reply + " " + self.messages["human_offer"]["english"]] if rag else [self.messages["human_offer"]["english"]]
            else:
                ticket = None
                out = [rag.reply if rag else "Sorry, I could not help with that just now. Please try again."]
            if self.demo_mode and not state.get("notice_sent"):
                out.insert(0, self.messages["demo_notice"]["english"]); state["notice_sent"] = True
            out = queued_messages + out
            out = [msg[i:i+600] for msg in out for i in range(0, len(msg), 600)] or ["Sorry, I could not help with that just now."]
            if rag:
                state["last_kb_ids"] = [e.id for e in rag.entries]
                state["last_intent"] = rag.reason_code
            state["last_query_hash"] = __import__("hashlib").sha256(clean.casefold().encode()).hexdigest()
            state["turns"].append({"role":"assistant", "text":mask_pii(" ".join(out))})
            state["turns"] = state["turns"][-10:]
            self.store.append_message(sender_hash, None, "assistant", " ".join(out), when)
            self.store.save_session(sender_hash, state, when)
            result = BotReply(out, ticket if guess.action in {"support","escalate","kb_first_aid_ticket"} else None,
                              {"decision":guess.action.upper(),"reason":guess.reason_code or (rag.reason_code if rag else "internal_error"),
                               "kb_ids":[e.id for e in rag.entries] if rag else [],"priority":guess.priority,
                               "confidence":rag.confidence if rag else 0})
            self.store.processed(message_id, sender_hash, result.__dict__, when)
            self._write_trace(result, sender_hash, when)
            return result
        except Exception as exc:
            # Safe apology and masked trace on any internal exception.
            ticket = self._ticket(sender_hash, when, clean, None, type("R", (), {"priority":"P3", "reason_code":"internal_error"})(), [])
            reply = BotReply(["Sorry, something went wrong. I have created a support ticket for follow-up."], ticket,
                             {"decision":"HANDOFF","reason":"internal_error","priority":"P3","kb_ids":[],"internal_error_type":type(exc).__name__,"internal_error_line":__import__("traceback").extract_tb(exc.__traceback__)[-1].lineno,"internal_error_trace":[{"file":__import__("pathlib").Path(frame.filename).name,"line":frame.lineno,"function":frame.name} for frame in __import__("traceback").extract_tb(exc.__traceback__)]})
            self._write_trace(reply, sender_hash, when)
            return reply

    def _identity_ok(self, sender):
        phone = re.sub(r"\D", "", sender)
        return any(re.sub(r"\D", "", item.get("sender", "")) == phone for item in self.learners)

    def _escalation_message(self, ticket, language, now):
        key = language.casefold() if language.casefold() in {"english", "hinglish"} else "english"
        template = self.messages["escalation"][key]["customer"]
        return template.format(ticket_id=ticket["ticket_id"], eta=ticket["sla_deadline"])

    def _write_trace(self, reply, sender_hash, now):
        folder = self.root / "data/traces"; folder.mkdir(parents=True, exist_ok=True)
        name = now.strftime("%Y%m%d") + ".jsonl"
        with (folder / name).open("a", encoding="utf-8") as f:
            f.write(json.dumps({"sender":sender_hash[:12],"reply":{**reply.__dict__,"messages":[mask_pii(item) for item in reply.messages]}}, ensure_ascii=False) + "\n")
