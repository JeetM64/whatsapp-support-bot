# Local chat demo

This UI uses synthetic SAMPLE DATA. The chat page is served by FastAPI; it does not use WhatsApp branding, external fonts, a CDN, or an LLM by default. Demo ticket fixtures are stored separately from ordinary local runs.

## Run

From `C:\dev\customer-support` in PowerShell 7:

```powershell
$env:PYTHONUTF8 = "1"
$env:ENV = "demo"
.\.venv\Scripts\python.exe -m src.app seed-demo
.\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. The seeded database is `data/demo/app.db`; running the seed command again is idempotent. Do not use real customer data in this demo.

## Agent inbox and founder dashboard

- Open `http://127.0.0.1:8000/agent`. Enter `AGENT_API_KEY` from the local `.env` file; it is held only in page memory and cleared when you sign out or reload. The protected ticket APIs use the Bearer header.
- Open `http://127.0.0.1:8000/founder` for aggregate counts and rates. The public metrics response contains no message text, ticket identifiers, or phone numbers. It displays a Demo data label when `ENV=demo`.
- In demo mode the server also seeds the separate demo database on startup when it contains no tickets.

## Manual click checklist

1. Open `/` and confirm the SAMPLE DATA and masked-logging banner.
2. Tab through the page and check visible keyboard focus on buttons and the message field.
3. Click **fee kitni hai** and check the chat bubble and typing indicator.
4. Click **Will I get a certificate?** and inspect the returned answer.
5. Click **payment cut gaya par access nahi aaya** and check any handoff banner.
6. Click **refund milega?** and use a quick-reply option if the API returns one.
7. Click **Are certificates AICTE approved?** and expand **Why this answer?**.
8. Click **Which domains are available?** and inspect decision, reason, KB ids, confidence, and mode.
9. Enter `<script>alert(1)</script>` as a message and confirm it appears as inert text.
10. Click **New chat** and send another message; confirm the conversation clears and a new per-tab sender id is generated.
11. Open `/agent`; submit a wrong key and confirm no ticket list appears.
12. Sign in with the agent key; verify priority, status, demo badges, filters, and the live SLA countdown.
13. Open a ticket, review the masked transcript and summary, use the suggested reply, send it, and check the needs-template message.
14. Resolve an open demo ticket and confirm its status changes; sign out and confirm the key field is empty.
15. Open `/founder`; check the Demo data badge, aggregate charts, and hours-saved assumption input. Change minutes per message and verify the estimate updates.
