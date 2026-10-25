# Part 3 logs and Part 4 API

## Conversation logs

`python -m src.app replay "samples/replay/*.yaml"` runs the eight scripted demos using the no-LLM provider and an isolated SQLite store. It writes `samples/conversation_logs.md` with masked customer messages, customer-visible replies, ticket outcomes, and internal debug metadata. Live app records are stored in `data/app.db`; masked diagnostic traces are under `data/traces/` and excluded from Git. Replay does not write live traces or use the project database.

## HTTP API

Install the pinned dependencies from `requirements.txt`, copy `.env.example` to `.env`, and set non-empty random `APP_SECRET` and `AGENT_API_KEY` values. Keep channel credentials empty in local demo mode. `ENV=dev` permits webhook signature bypass only when the matching secret is absent, and logs a warning. Production requires signature secrets. Never place real customer numbers or credentials in replay scripts.

Run locally with:

```powershell
pwsh -NoProfile -Command "$PSVersionTable.PSVersion"
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Routes: `GET /health`, `POST /chat`, `GET|POST /webhook/meta`, `POST /webhook/twilio`, and Bearer-key protected `/api/tickets`, `/api/tickets/{ticket_id}`, `/reply`, `/resolve`, and `/api/metrics`. The development app defaults to `FakeChannel`; API-created RAG engines use `NoneProvider`. Outbound Meta messages are only enabled outside `ENV=dev`. `python -m src.api.simulate "<text>" --sender demo --channel meta` runs a local simulation.

Webhook callbacks acknowledge Meta delivery before background processing, validate HMAC signatures outside the documented development bypass, ignore status-only events, and persist message-id deduplication through the Bot store. Twilio replies use TwiML. The API caps request bodies at 64 KiB, limits sender/IP traffic, masks persisted message text, and returns request IDs with generic errors.
