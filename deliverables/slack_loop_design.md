# Slack ask-a-human loop (design only)

```mermaid
sequenceDiagram
 participant B as Bot
 participant DB as SQLite ticket
 participant S as Slack
 participant H as Human
 B->>DB: Create ticket with reason, language, masked turns, KB ids
 B->>S: Post structured ask with ticket reference and unconfirmed field
 H->>S: Reply in thread
 S->>DB: Validate thread/ticket mapping and persist response
 DB-->>B: Human-confirmed answer for current session only
 S-->>B: Timeout or missing mapping
 B->>DB: Keep ticket open and record timeout
```

Payload: ticket id, reason code, masked customer id, language, intent, exact question, KB ids, confidence, candidate answer and requested confirmation. Never post payment credentials, OTPs or unmasked personal details. Thread replies are matched to the existing ticket; invalid or late replies are ignored and the ticket remains open. On timeout, tell the customer the team will follow up; do not invent an answer. Maps to the existing tickets and ticket_messages tables.
