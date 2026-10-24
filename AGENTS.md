# Project Agent Context

## Machine and shell
- Windows 11 Home Single Language, version 26H2, build 26300.9711.
- Use PowerShell 7.6.6 (`pwsh`, at `C:\Program Files\PowerShell\7\pwsh.exe`) for all commands.
- Windows PowerShell 5.1 (`powershell.exe`) is broken (startup error 80070002). Never call it or try to repair it as part of this task.
- Before running anything, verify the real shell with `pwsh -NoProfile -Command "$PSVersionTable.PSVersion"` and expect 7.6.6. If a tool uses another shell, explicitly invoke pwsh or run scripts with `pwsh -File`.

## Safety rules
Ask first before editing the registry; touching the GAC or system DLLs; changing system permissions or execution policy; installing or uninstalling system-wide software; deleting files outside this project folder; recursive forced deletion; `git reset --hard`; `git clean`; force-push; or destructive repair commands.
If a command fails, read the error, find the root cause, and propose the smallest safe fix. Do not assume every failure is PowerShell. Do not reinstall tools that already work (node, npm, git, python, docker).

## Windows habits
- Python venv: `py -3.12 -m venv .venv`; use `..\.venv\Scripts\python.exe` directly. Never change execution policy.
- Use `$env:NAME = "value"` for environment variables; use semicolons or separate lines; quote paths with spaces.
- Set `$env:PYTHONUTF8 = "1"` for Unicode output and UTF-8 file I/O.
- Prefer cross-platform code and add `.gitattributes` for line endings.
- If a package needs a C++ compiler, try a prebuilt wheel/newer version first and tell the user before installing Build Tools.
- For the WhatsApp webhook demo use a tunnel (ngrok or cloudflared) and tell the user which one is needed.
- For VS Code/Cursor, check the integrated terminal shell. If it uses powershell.exe, advise setting `terminal.integrated.defaultProfile.windows` to PowerShell with pwsh 7; do not silently edit settings.

## Project
- WhatsApp customer-support bot for Internship Studio (Founder Office Intern assignment IS-FO-INT-WA-01, due 28 Oct 2026).
- Stack: FastAPI, ChromaDB RAG, React/Next.js frontend, Twilio or Meta WhatsApp sandbox.
- Build one stage at a time. After each stage run tests, show actual output, and stop for user review.
- Company data (fees, refund terms, links, contacts) is mock unless supplied as a verified fact. Label it SAMPLE DATA. The bot answers only from the knowledge base and never invents answers.
- No secrets in the repo; use `.env` plus `.env.example`.
- After each stage say what changed, exact pwsh commands to run it, and the next stage.

## Truth policy
- Real company facts live only in `kb/verified_facts.yaml`, populated by the user from verified company sources.
- Other content is mock, marked `mock: true` and SAMPLE DATA in KB, UI, logs, and documentation.
- Do not present invented fees, durations, refund terms, links, phone numbers, approvals, accreditation, AICTE, or validity claims as real.
- The bot answers only from the KB. Without a supporting entry, state that the answer is not available and route to a human.
- Do not state unverified third-party claims about the company as fact; give only verifiable steps and offer a human.

## Customer and conversation design
- Main users are Indian 2nd/3rd-year B.Tech/BCA/BSc/MBA students and freshers; also parents, college TPOs/partners, and existing learners.
- Be calm, respectful, brief (<=600 characters), acknowledge frustration first, never blame, do not over-promise, and mirror the user's language (including Hinglish).
- Handle trust/validity questions with verifiable steps first and offer a human; escalate hostility or money loss.

## Architecture requirements
- Pipeline files in `src/`: `main.py`, `rag_engine.py`, `guardrails.py`, `session_memory.py`, `handoff.py`, `analytics.py`, `config.py`, `models.py`.
- L0 rules (English + Hindi/Hinglish): explicit human request, abuse, legal/consumer-court/chargeback threat, scam claim with money lost, repeated failure, or shared OTP/card/Aadhaar (mask and warn) -> escalate.
- L1 classifier JSON: intent, language, sentiment, urgency, needs_human, confidence.
- L2 retrieval: ChromaDB, multilingual embeddings, hybrid keyword match, similarity threshold.
- L3 generation uses retrieved entries only and tracks KB IDs.
- L4 post-check requires every claim to be supported by retrieved entries; otherwise discard and escalate.
- Status questions (payment/certificate) must never be guessed; use mock lookup now and Slack ask-a-human loop as bonus.
- Session memory: last N turns + resolved entities, TTL, PII-masked; resolve follow-ups.
- WhatsApp: webhook verification token, X-Hub-Signature-256 check, message-ID dedupe, 24h-window handling, rate limits, and out-of-hours reply with ticket ID and expected reply time.
- Handoff JSON fields: ticket_id, reason_code, priority, customer_masked_id, language, sentiment, intent, summary_3_lines, last_5_turns, kb_ids_tried, confidence, suggested_reply, sla_deadline.

## Frontend, evaluation, and deliverables
- Frontend: WhatsApp-style simulator with SAMPLE DATA banner and human handoff state; agent inbox with context/reason/SLA/suggested reply/send reply; founder dashboard with metrics computed from real logged runs.
- Evaluation: 50 messages including English, Hinglish, typos, one-word, angry, trust, out-of-KB, follow-ups, and prompt-injection attempts. Report answered correctly, correctly escalated, wrongly escalated, hallucinations (target 0), and injection resisted.
- Deliver: `kb/` CSV, JSON build, verified facts, mock learners; `src/`, pytest, README; 8 real transcripts from bot runs; eval results; frontend; `docs/Solution_Document.md` (<=6-page PDF) with assumptions, architecture, KB, intents, escalations, stack, cost, risks, rollout and go-live checklist; optional Slack loop; requirements-to-file checklist and 5-minute demo script.
- Build order: Stage 0 environment/skeleton/template; 1 KB and build/report; 2 RAG + tests; 3 guardrails + tests; 4 memory/handoff/CLI; 5 eval/logs; 6 FastAPI + WhatsApp webhook; 7 frontend; 8 solution document + PDF; 9 Slack bonus; 10 checklist/demo. Stop after each stage for review.
