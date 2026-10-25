from __future__ import annotations
import argparse, base64, hashlib, hmac, json, os, secrets
from pathlib import Path
from src.api.channels import FakeChannel
from src.app.bot import Bot
from src.app.store import Store
from src.rag.engine import RagEngine
from src.rag.providers import NoneProvider

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("text"); parser.add_argument("--sender",default="demo"); parser.add_argument("--channel",choices=["meta","twilio"],default="meta")
    args=parser.parse_args(); root=Path.cwd().resolve(); mid="sim-"+secrets.token_hex(6)
    class QuietBot(Bot):
        def _write_trace(self, *args, **kwargs): pass
    bot=QuietBot(root,engine=RagEngine(root,provider=NoneProvider()),store=Store(root,secret="local-simulator"))
    sender="whatsapp:"+"".join(c for c in args.sender if c.isdigit())
    if args.channel == "meta":
        secret=os.getenv("META_APP_SECRET", "")
        if not secret: raise SystemExit("Safe simulation error: META_APP_SECRET is required; value was not displayed.")
        raw=json.dumps({"entry":[{"changes":[{"value":{"messages":[{"id":mid,"from":"".join(c for c in args.sender if c.isdigit()),"type":"text","text":{"body":args.text}}]}}]}]},separators=(",",":")).encode()
        signature="sha256="+hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
        verified=hmac.compare_digest(signature,"sha256="+hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest())
    else:
        token=os.getenv("TWILIO_AUTH_TOKEN", "")
        if not token: raise SystemExit("Safe simulation error: TWILIO_AUTH_TOKEN is required; value was not displayed.")
        params={"Body":args.text,"From":"whatsapp:"+args.sender,"MessageSid":mid}
        url="http://localhost/webhook/twilio"
        canonical=url+"".join(k+params[k] for k in sorted(params))
        signature=base64.b64encode(hmac.new(token.encode(),canonical.encode(),hashlib.sha1).digest()).decode()
        verified=hmac.compare_digest(signature,base64.b64encode(hmac.new(token.encode(),canonical.encode(),hashlib.sha1).digest()).decode())
    if not verified: raise SystemExit("Safe simulation error: signature verification failed.")
    result=bot.handle_message(sender,args.text,mid,args.channel)
    print(json.dumps({"channel":args.channel,"signed_payload":"verified locally","messages":result.messages,"ticket":result.ticket,"debug":result.debug},ensure_ascii=False,indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
