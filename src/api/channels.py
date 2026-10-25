from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class Channel(Protocol):
    name: str
    def send(self, recipient: str, text: str) -> None: ...


@dataclass
class FakeChannel:
    name: str = "fake"
    sent: list[tuple[str, str]] = field(default_factory=list)
    def send(self, recipient: str, text: str) -> None:
        self.sent.append((recipient, text))


class WebChannel(FakeChannel):
    name = "web"


class MetaChannel:
    name = "meta"
    def send(self, recipient: str, text: str) -> None:
        import httpx
        import os
        token, phone_id = os.getenv("META_ACCESS_TOKEN", ""), os.getenv("META_PHONE_NUMBER_ID", "")
        if not token or not phone_id:
            raise RuntimeError("Meta channel is not configured")
        for part in (text[i:i + 600] for i in range(0, len(text), 600)):
            for attempt in range(2):
                try:
                    response = httpx.post(
                        f"https://graph.facebook.com/v20.0/{phone_id}/messages",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"messaging_product": "whatsapp", "to": recipient, "type": "text", "text": {"body": part}},
                        timeout=httpx.Timeout(8.0),
                    )
                    if response.status_code >= 500 and attempt == 0: continue
                    response.raise_for_status()
                    break
                except httpx.RequestError:
                    if attempt: raise


class TwilioChannel:
    name = "twilio"
    def send(self, recipient: str, text: str) -> None:
        # Twilio inbound messages are answered synchronously with TwiML.
        return None
