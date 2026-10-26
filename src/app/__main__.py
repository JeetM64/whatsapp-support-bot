from __future__ import annotations
import argparse, glob, json, os, sys, tempfile
from datetime import datetime
from pathlib import Path
import yaml
from src.rag.config import load_dotenv
from src.rag.engine import RagEngine, mask_pii
from src.rag.providers import NoneProvider
from .bot import Bot
from .store import Store

def _root() -> Path:
    return Path.cwd().resolve()

def _stamp(value: str | None):
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value) if value else None

def _ticket_print(ticket):
    fields = {key: ticket.get(key) for key in ("ticket_id","reason_code","priority","status","customer_masked_id","sla_deadline")}
    print(json.dumps(fields, ensure_ascii=False, indent=2))

def run_chat(args):
    root=_root(); load_dotenv(root)
    bot=Bot(root, engine=RagEngine(root), store=Store(root))
    print("Demo support chat. SAMPLE DATA only. Enter /quit to end.")
    while True:
        try: text=input("you> ")
        except EOFError: break
        if text.strip()=="/quit": break
        result=bot.handle_message(args.sender,text,None,"cli",_stamp(args.now))
        for message in result.messages: print("bot>",message)
        if result.ticket: _ticket_print(result.ticket)
        if args.debug: print("debug>",json.dumps(result.debug,ensure_ascii=False))
    return 0

def run_tickets(args):
    root=_root(); load_dotenv(root); store=Store(root)
    cmd=args.ticket_cmd
    if cmd=="list":
        for ticket in store.list_tickets(): _ticket_print(ticket)
        return 0
    if cmd=="show":
        ticket=store.ticket(args.ticket_id)
        if not ticket: print("Ticket not found."); return 1
        print(json.dumps(ticket,ensure_ascii=False,indent=2)); return 0
    if cmd=="reply":
        if not store.ticket(args.ticket_id): print("Ticket not found."); return 1
        store.queue_reply(args.ticket_id,args.text); print("Reply queued for the customer's next chat."); return 0
    if cmd=="resolve":
        ticket=store.resolve(args.ticket_id)
        if not ticket: print("Ticket not found."); return 1
        print(f"{args.ticket_id} resolved."); return 0
    return 2

def run_seed_demo():
    root=_root(); load_dotenv(root)
    os.environ["ENV"]="demo"
    from .demo_seed import DEMO_CONVERSATIONS
    store=Store(root)
    created=store.seed_demo_conversations(DEMO_CONVERSATIONS)
    print(f"Demo seed complete: {created} new conversations; {len(DEMO_CONVERSATIONS)} total fixtures; database={store.path.relative_to(root)}")
    return 0

def run_replay(patterns):
    root=_root(); load_dotenv(root)
    files=[]
    for pattern in patterns:
        matches=glob.glob(pattern)
        files.extend(Path(name) for name in (matches or [pattern]) if Path(name).is_file())
    if not files: raise FileNotFoundError("No replay YAML scripts matched the given paths.")
    logs=["# Conversation replay logs","","> SAMPLE DATA. Customer values are masked before persistence.",""]
    traces=[]
    temp_root = root / ".tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    class ReplayBot(Bot):
        def _write_trace(self, reply, sender_hash, now):
            return
    replay_dir = Path(tempfile.mkdtemp(prefix="conversation-replay-", dir=temp_root))
    engine=RagEngine(root, provider=NoneProvider())
    bot=ReplayBot(root,engine=engine,store=Store(replay_dir, secret="isolated-replay-secret"))
    for path in sorted(set(files)):
        script=yaml.safe_load(path.read_text(encoding="utf-8"))
        sender=script.get("sender",f"replay:{path.stem}")
        logs.extend([f"## {script['title']}",""])
        for index, turn in enumerate(script.get("turns",[]),1):
            user=turn["user"]
            logs.extend([f"**Customer:** {mask_pii(user)}"])
            reply=bot.handle_message(sender,user,turn.get("message_id",f"{path.stem}-{index}"),"replay",_stamp(script.get("now")))
            for message in reply.messages: logs.append(f"**Bot:** {mask_pii(message)}")
            logs.append(f"**Debug:** decision={reply.debug.get('decision')} reason={reply.debug.get('reason')} KB ids={reply.debug.get('kb_ids')} priority={reply.debug.get('priority')}")
            if reply.ticket: logs.append(f"Ticket: {reply.ticket['ticket_id']}")
            logs.append("")
            traces.append({"script":path.name,"turn":index,"sender_masked":reply.ticket.get("customer_masked_id") if reply.ticket else bot.store.sender_hash(sender)[:12],"messages":[mask_pii(m) for m in reply.messages],"ticket":reply.ticket,"debug":reply.debug})
    (root/"samples/conversation_logs.md").write_text("\n".join(logs),encoding="utf-8")
    print(f"Replay complete: {len(files)} scripts, {len(traces)} turns.")
    print(f"Conversation log: {root / 'samples/conversation_logs.md'}")
    for ticket in bot.store.list_tickets(): _ticket_print(ticket)
    return 0

def main():
    parser=argparse.ArgumentParser(prog="python -m src.app")
    sub=parser.add_subparsers(dest="command",required=True)
    chat=sub.add_parser("chat"); chat.add_argument("--sender",required=True); chat.add_argument("--debug",action="store_true"); chat.add_argument("--now")
    tickets=sub.add_parser("tickets"); ts=tickets.add_subparsers(dest="ticket_cmd",required=True)
    ts.add_parser("list")
    show=ts.add_parser("show"); show.add_argument("ticket_id")
    reply=ts.add_parser("reply"); reply.add_argument("ticket_id"); reply.add_argument("text")
    resolve=ts.add_parser("resolve"); resolve.add_argument("ticket_id")
    replay=sub.add_parser("replay"); replay.add_argument("scripts",nargs="+")
    sub.add_parser("seed-demo")
    args=parser.parse_args()
    try:
        if args.command=="chat": return run_chat(args)
        if args.command=="tickets": return run_tickets(args)
        if args.command=="seed-demo": return run_seed_demo()
        return run_replay(args.scripts)
    except Exception as exc:
        import traceback
        frame=traceback.extract_tb(exc.__traceback__)[-1]
        print(f"Safe app error: {type(exc).__name__} at {Path(frame.filename).name}:{frame.lineno}.")
        return 1

if __name__=="__main__": raise SystemExit(main())
