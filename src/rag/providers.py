from __future__ import annotations

import json
import os
from collections import deque
from dataclasses import dataclass
from typing import Any, Protocol


class Provider(Protocol):
    name: str

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        timeout: float,
    ) -> tuple[dict[str, Any], dict[str, int | None]]: ...


class ProviderConfigError(RuntimeError):
    pass


class NoneProvider:
    name = "none"

    def generate_json(
        self, system: str, user: str, schema: dict[str, Any], timeout: float
    ) -> tuple[dict[str, Any], dict[str, int | None]]:
        raise RuntimeError("NoneProvider is extractive-only")


class FakeProvider:
    name = "fake"

    def __init__(self, scripted: list[Any] | None = None) -> None:
        self.scripted = deque(scripted or [])
        self.calls: list[dict[str, str]] = []

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        timeout: float,
    ) -> tuple[dict[str, Any], dict[str, int | None]]:
        self.calls.append({"system": system, "user": user})
        if not self.scripted:
            raise RuntimeError("FakeProvider has no scripted response")
        response = self.scripted.popleft()
        if isinstance(response, BaseException):
            raise response
        if callable(response):
            response = response(system, user, schema, timeout)
        if not isinstance(response, dict):
            raise ValueError("FakeProvider response must be a JSON object")
        if "json" in response and "reply" not in response:
            response = json.loads(str(response["json"]))
        usage = response.pop("_usage", {})
        return response, {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        }


@dataclass
class SDKProvider:
    name: str
    api_key: str
    model: str
    max_tokens: int = 256
    temperature: float = 0.0

    def _json_response(self, raw: str) -> dict[str, Any]:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("provider response was not a JSON object")
        return value


class GeminiProvider(SDKProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int = 256) -> None:
        super().__init__("gemini", api_key, model, max_tokens=max_tokens)

    def generate_json(self, system, user, schema, timeout):
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=int(timeout * 1000)),
        )
        response = client.models.generate_content(
            model=self.model,
            contents=f"{system}\n\n{user}",
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        raw = response.text or ""
        usage = getattr(response, "usage_metadata", None)
        return self._json_response(raw), {
            "input_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
        }


class AnthropicProvider(SDKProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int = 256) -> None:
        super().__init__("anthropic", api_key, model, max_tokens=max_tokens)

    def generate_json(self, system, user, schema, timeout):
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key, timeout=timeout, max_retries=0)
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = "".join(
            getattr(part, "text", "")
            for part in response.content
            if getattr(part, "type", None) == "text"
        )
        return self._json_response(raw), {
            "input_tokens": getattr(response.usage, "input_tokens", None),
            "output_tokens": getattr(response.usage, "output_tokens", None),
        }


def create_provider(name: str | None, max_tokens: int = 256) -> Provider:
    selected = (name or os.getenv("LLM_PROVIDER", "none")).strip().casefold()
    if selected in {"", "none"}:
        return NoneProvider()
    if selected == "fake":
        return FakeProvider()
    if selected == "gemini":
        key = os.getenv("GEMINI_API_KEY", "")
        model = os.getenv("GEMINI_MODEL", "")
        if not key or not model:
            raise ProviderConfigError(
                "Gemini requires GEMINI_API_KEY and GEMINI_MODEL in .env; values were not displayed."
            )
        return GeminiProvider(key, model, max_tokens=max_tokens)
    if selected == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY", "")
        model = os.getenv("ANTHROPIC_MODEL", "")
        if not key or not model:
            raise ProviderConfigError(
                "Anthropic requires ANTHROPIC_API_KEY and ANTHROPIC_MODEL in .env; values were not displayed."
            )
        return AnthropicProvider(key, model, max_tokens=max_tokens)
    raise ProviderConfigError(f"Unsupported provider: {selected}")
