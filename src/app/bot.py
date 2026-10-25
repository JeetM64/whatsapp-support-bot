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

def _next_open(
    t: datetime,
    *,
    start_hour: int = 11,
    end_hour: int = 19,
    working_weekdays: set[int] | None = None,
) -> datetime:
    t = t.astimezone(IST)
    working_weekdays = working_weekdays or set(range(6))
    while t.weekday() not in working_weekdays:
        t = (t + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if t.hour < start_hour:
        return t.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if t.hour >= end_hour:
        t = (t + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
        while t.weekday() not in working_weekdays:
            t += timedelta(days=1)
    return t

def sla_deadline(
    now: datetime,
    priority: str,
    hours: int,
    *,
    start_hour: int = 11,
    end_hour: int = 19,
    working_weekdays: set[int] | None = None,
    business_days: int | None = None,
) -> datetime:
    working_weekdays = working_weekdays or set(range(6))
    t = _next_open(now, start_hour=start_hour, end_hour=end_hour, working_weekdays=working_weekdays)
    if business_days is not None:
        target = t
        remaining_days = business_days
        while remaining_days:
            target = (target + timedelta(days=1)).replace(second=0, microsecond=0)
            while target.weekday() not in working_weekdays:
                target += timedelta(days=1)
            remaining_days -= 1
        return target
    remaining = float(hours)
    while remaining > 0:
        t = _next_open(t, start_hour=start_hour, end_hour=end_hour, working_weekdays=working_weekdays)
        close = t.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        available = (close - t).total_seconds() / 3600
        if remaining <= available: return t + timedelta(hours=remaining)
        remaining -= available
        t = close + timedelta(seconds=1)
        t = _next_open(t, start_hour=start_hour, end_hour=end_hour, working_weekdays=working_weekdays)
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
        business_days = self.hours.get("sla_business_days", {}).get(priority)
        business_hours = self.hours.get("business_hours", {})
        weekdays = business_hours.get("weekdays", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
        weekday_map = {name: index for index, name in enumerate((
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        ))}
        weekday_numbers = {weekday_map[day] for day in weekdays if day in weekday_map}
        start_hour = int(str(business_hours.get("start", "11:00")).split(":", 1)[0])
        end_hour = int(str(business_hours.get("end", "19:00")).split(":", 1)[0])
        deadline = sla_deadline(
            now,
            priority,
            hrs,
            start_hour=start_hour,
            end_hour=end_hour,
            working_weekdays=weekday_numbers,
            business_days=int(business_days) if business_days is not None else None,
        )
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
            refund_flow_override = False
            refund_selection = None
            if state.get("pending_refund_batch"):
                if re.search(r"\bregular\b|regular batch|रेगुलर", clean, re.I):
                    refund_selection = "regular"
                elif re.search(r"refund (?:guarantee )?program|program batch|रिफंड प्रोग्राम", clean, re.I):
                    refund_selection = "refund_program"
            if refund_selection:
                refund_language = state.pop("pending_refund_language", detect_language(clean))
                state["batch_type"] = refund_selection
                state["pending_refund_batch"] = False
                if refund_language == "Hinglish":
                    raw_text = ("Regular batch mein refund ki kya policy hai?" if refund_selection == "regular"
                                else "Refund program ki conditions kya hain?")
                else:
                    raw_text = ("I am in the Regular batch and want a refund. What is the policy?"
                                if refund_selection == "regular" else "What are the Refund Guarantee Program conditions?")
                refund_flow_override = True
            else:
                refund_request = bool(
                    re.search(
                        r"\b(refund policy|refund rules|refund eligibility|can i get a refund|"
                        r"what is the refund|will i (?:get|receive) a refund|am i eligible for a refund|"
                        r"want a refund|refund me|my refund|refund chahiye|refund milega|"
                        r"paise wapas|paisa wapas|money back|cancel my (?:enrolment|enrollment))\b|रिफंड चाहिए|पैसे वापस",
                        clean,
                        re.I,
                    )
                )
                duplicate_payment = self.guard.matches("R12_DUPLICATE_PAYMENT", clean)
                if refund_request and not duplicate_payment and not state.get("batch_type"):
                    state["pending_refund_batch"] = True
                    state["pending_refund_language"] = detect_language(clean)
                    clarification = (
                        "Jawab dene se pehle batayein: aap Regular batch mein hain ya Refund program batch mein?"
                        if detect_language(clean) == "Hinglish"
                        else "Before I answer a refund question, are you in the Regular batch or the Refund program batch?"
                    )
                    notice_language = detect_language(clean).casefold()
                    notice_language = notice_language if notice_language in {"english", "hinglish"} else "english"
                    out = queued_messages + ([self.messages["demo_notice"][notice_language]] if self.demo_mode and not state.get("notice_sent") else []) + [clarification]
                    state["notice_sent"] = state.get("notice_sent", False) or self.demo_mode
                    state["turns"].append({"role":"assistant", "text":mask_pii(clarification)})
                    state["turns"] = state["turns"][-10:]
                    self.store.append_message(sender_hash, None, "assistant", clarification, when)
                    self.store.save_session(sender_hash, state, when)
                    result = BotReply(out, None, {"decision":"CLARIFY", "reason":"refund_batch_type", "kb_ids":[]})
                    self.store.processed(message_id, sender_hash, result.__dict__, when)
                    self._write_trace(result, sender_hash, when)
                    return result
                if refund_request and state.get("batch_type"):
                    raw_text = (
                        "I am in the Regular batch and want a refund. What is the policy?"
                        if state["batch_type"] == "regular"
                        else "What are the Refund Guarantee Program conditions?"
                    )
                    refund_flow_override = True
            human_offer_accepted = bool(
                state.get("pending_human_offer")
                and re.search(r"\b(yes|yeah|yep|haan|ha|ji|sure|okay|ok|connect|go ahead)\b", clean, re.I)
            )
            if human_offer_accepted:
                state["pending_human_offer"] = False
            if state.get("handed_off"):
                open_ticket = self.store.ticket(state.get("open_ticket_id", ""))
                if open_ticket and open_ticket.get("status") == "open":
                    self.store.append_ticket_message(open_ticket["ticket_id"], clean)
                    human_messages = queued_messages
                    if raw_text.strip().casefold() in {"status", "ticket status"}:
                        lang = detect_language(clean).casefold()
                        lang = lang if lang in {"english", "hinglish"} else "english"
                        out = human_messages + [self.messages["ticket_status"][lang].format(ticket_id=open_ticket["ticket_id"], eta=open_ticket["sla_deadline"])]
                    else:
                        out = human_messages
                    result = BotReply(out, open_ticket, {"decision":"HANDOFF","reason":"ticket_open","priority":open_ticket.get("priority"),"kb_ids":[]})
                    self.store.save_session(sender_hash, state, when); self.store.processed(message_id, sender_hash, result.__dict__, when)
                    return result
                state["handed_off"] = False
                state["open_ticket_id"] = None            # Handle CLARIFY selection and terse follow-up against stored options/KB id.
            follow = raw_text.strip().casefold()
            if refund_flow_override or human_offer_accepted:
                pass
            elif state.get("pending_options") and re.match(r"^(1|2|3|one|two|three|payment wala|certificate wala)$", follow):
                options = state["pending_options"]
                idx = 0 if follow in {"1","one","payment wala"} else 1
                if idx < len(options): raw_text = f"{raw_text} {options[idx]}"
            elif (
                len(follow.split()) <= 4
                and state.get("last_kb_ids")
                and re.match(r"^(and|also|what about|how about|aur|iska|iske|uska|uske|there|that|it|fee|price|duration)\b", follow)
            ):
                prior_id = state["last_kb_ids"][0]
                prior = self.engine.retriever.entries.get(prior_id, {}) if self.engine else {}
                raw_text = f"{raw_text} about {prior.get('question', prior_id)}"
            else:
                raw_text = clean
            same_query = state.get("last_query_hash") == __import__("hashlib").sha256(clean.casefold().encode()).hexdigest()
            # L0 runs first; deterministic RAG is called only if no hard rule fires.
            if human_offer_accepted:
                from src.guard import GuardResult
                from types import SimpleNamespace
                guess = GuardResult("human_offer_accepted", "P3", "escalate")
                rag = SimpleNamespace(
                    language=detect_language(clean), confidence=0.0, entries=[],
                    reason_code="human_offer_accepted", decision=SimpleNamespace(value="NO_MATCH")
                )
            else:
                guess = self.guard.classify(clean, frustration_loop=state.get("clarify_no_match_streak",0) >= 2 or same_query,
                                            status_authorized=self._identity_ok(sender))
                rag = None
            if refund_flow_override and guess.reason_code == "refund_action":
                from src.guard import GuardResult
                guess = GuardResult()
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
            if rag and getattr(rag, "decision", None) and rag.decision.value == "NO_MATCH" and (
                guess.action == "continue" or rag.reason_code == "out_of_scope_request"
            ):
                top_entry = self.engine.retriever.entries.get(rag.entries[0].id, {}) if self.engine and rag.entries else {}
                high_risk_kb = bool(top_entry.get("escalate_if_unmatched")) or top_entry.get("risk_level") == "high"
                if guess.action == "continue" and high_risk_kb and rag.reason_code != "prompt_injection_blocked":
                    guess = self.guard.classify(clean, unmatched_high_risk=True, status_authorized=self._identity_ok(sender))
                self.store.gap(sender_hash, clean, when)
            if rag and rag.decision.value == "CLARIFY" and self.engine:
                option_limit = 2 if rag.reason_code == "low_margin_entry_conflict" else 3
                state["pending_options"] = [self.engine.retriever.entries[e.id].get("question", e.id) for e in rag.entries if e.id in self.engine.retriever.entries][:option_limit]
            if guess.action == "continue" and rag and rag.decision.value in {"CLARIFY", "NO_MATCH"} and state.get("clarify_no_match_streak", 0) >= 1:
                from src.guard import GuardResult
                guess = GuardResult("frustration_loop", "P3", "escalate")
            if guess.action == "continue" and rag and rag.decision.value in {"CLARIFY", "NO_MATCH"}:
                state["clarify_no_match_streak"] = int(state.get("clarify_no_match_streak",0)) + 1
            elif guess.action == "continue": state["clarify_no_match_streak"] = 0
            same_answer_followup = bool(
                guess.action == "continue" and rag and rag.decision.value == "ANSWER" and rag.entries
                and state.get("last_answer_core") == rag.reply
                and set(state.get("last_kb_ids", [])) & {entry.id for entry in rag.entries}
            )
            if same_answer_followup:
                lang = rag.language.casefold() if rag.language.casefold() in {"english", "hinglish"} else "english"
                previous_ack = bool(state.get("repeat_ack_sent"))
                refund_eligibility_followup = bool(
                    any(entry.id == "CAT-048" for entry in rag.entries)
                    and re.search(r"\b(completed|finished|met|done|poore|kiye|submit|attendance|assignments)\b", clean, re.I)
                )
                if refund_eligibility_followup:
                    out = [self.messages["repeat_answer"][lang] if previous_ack else self.messages["refund_review"][lang]]
                else:
                    out = [self.messages["repeat_answer"][lang]]
                state["pending_human_offer"] = True
                state["repeat_ack_sent"] = True
                ticket = None
            elif guess.action == "warn":
                lang = (rag.language if rag else detect_language(clean)).casefold()
                lang = lang if lang in {"english", "hinglish"} else "english"
                if state.get("sensitive_warned"):
                    out = [self.messages["sensitive_data"][lang]]
                else:
                    out = [self.messages["sensitive_data"][lang]]
                    state["sensitive_warned"] = True
            elif guess.action == "support":
                lang = (rag.language if rag else detect_language(clean)).casefold()
                lang = lang if lang in {"english", "hinglish"} else "english"
                reply_text = self.messages["distress"][lang]
                ticket = self._ticket(sender_hash, when, clean, rag, guess, state["turns"])
                out = [reply_text + " " + self._escalation_message(ticket, rag.language if rag else "English", when)]
                state.update(handed_off=True, open_ticket_id=ticket["ticket_id"])
            elif guess.action in {"escalate", "kb_first_aid_ticket"}:
                ticket = self._ticket(sender_hash, when, clean, rag, guess, state["turns"])
                from src.rag.composer import strip_handoff_offer
                base = (
                    strip_handoff_offer(rag.reply, rag.language)
                    if guess.action == "kb_first_aid_ticket" and rag and rag.decision.value == "ANSWER"
                    else ""
                )
                escalation = self._escalation_message(ticket, rag.language if rag else "English", when)
                out = ([base] if base else []) + [escalation]
                state.update(handed_off=True, open_ticket_id=ticket["ticket_id"])
            elif guess.action == "offer_human":
                lang = (rag.language if rag else detect_language(clean)).casefold()
                lang = lang if lang in {"english", "hinglish"} else "english"
                if rag and rag.reason_code == "out_of_scope_request":
                    if re.search(r"\b(college|campus)\b", clean, re.I): topic = "college partnerships" if lang == "english" else "college partnership"
                    elif re.search(r"\b(corporate|employer|company|recruiter)\b", clean, re.I): topic = "company partnerships" if lang == "english" else "company partnership"
                    else: topic = "partnerships" if lang == "english" else "partnership"
                    out = [self.messages["out_of_scope"][lang].format(topic=topic)]
                else:
                    offer = self.messages["human_offer"][lang]
                    base = rag.reply if rag else ""
                    out = [base if offer.casefold() in base.casefold() else (base + " " + offer).strip()]
                state["pending_human_offer"] = True
            elif rag and rag.reason_code == "prompt_injection_blocked" and re.search(
                r"\b(refund|money back|money)\b|रिफंड|पैसे वापस", clean, re.I
            ):
                lang = rag.language.casefold() if rag.language.casefold() in {"english", "hinglish"} else "english"
                out = [self.messages["injection_refund"][lang]]
                state["pending_refund_batch"] = True
                state["pending_human_offer"] = True
                state["pending_refund_language"] = rag.language
            else:
                ticket = None
                out = [rag.reply if rag else "Sorry, I could not help with that just now. Please try again."]
                if rag and rag.decision.value == "NO_MATCH":
                    state["pending_human_offer"] = True
            if self.demo_mode and not state.get("notice_sent"):
                notice_language = (rag.language if rag else detect_language(clean)).casefold()
                notice_language = notice_language if notice_language in {"english", "hinglish"} else "english"
                out.insert(0, self.messages["demo_notice"][notice_language]); state["notice_sent"] = True
            out = queued_messages + out
            out = [msg[i:i+600] for msg in out for i in range(0, len(msg), 600)] or ["Sorry, I could not help with that just now."]
            if rag:
                state["last_kb_ids"] = [e.id for e in rag.entries]
                state["last_intent"] = rag.reason_code
                if rag.decision.value == "ANSWER": state["last_answer_core"] = rag.reply
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
            lang = detect_language(clean)
            escalation = self._escalation_message(ticket, lang, when)
            reply = BotReply([escalation], ticket,
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
