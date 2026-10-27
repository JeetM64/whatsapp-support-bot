# Hosting the demo

## Hugging Face Spaces (Docker)

1. Create a new Space and select the Docker SDK.
2. Run `pwsh -File .\deploy\make_space_bundle.ps1` and upload the contents of `.tmp\space-bundle`.
3. In Space Settings, add `AGENT_API_KEY` as a secret. Set `ENV=demo` and `PUBLIC_BASE_URL` to the Space URL. Set `TRUST_PROXY=true` only when deployed behind its trusted proxy.
4. Wait for the image build, open the Space URL, and check `/health`.
5. Check `/`, `/agent`, and `/founder`; sign in to `/agent` using the configured key.
6. Send a fee question and a Hinglish payment question in `/`.
7. Create an escalation and confirm it appears in the agent inbox.
8. Confirm founder metrics show the Demo data label and never contain message text.

Missing LLM credentials are expected: the default provider is `none`. Docker build and hosted deployment have not been live-verified in this workspace.
