from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from src.rag.composer import compose
from src.rag.config import RagConfig
from src.rag.models import LLMReply
from src.rag.providers import FakeProvider, NoneProvider
from src.rag.providers import _gemini_schema
from src.rag.providers import GeminiProvider
from src.rag.verifier import verify_reply

ROOT = Path(__file__).resolve().parents[1]


def test_gemini_schema_keeps_property_names_and_removes_unsupported_fields() -> None:
    schema = {
        "title": "Reply",
        "type": "object",
        "properties": {
            "reply": {"title": "Reply", "type": "string", "minLength": 1},
            "used_entry_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["reply", "used_entry_ids"],
        "additionalProperties": False,
    }
    result = _gemini_schema(schema)
    assert result == {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "used_entry_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["reply", "used_entry_ids"],
    }


class SameVectorEmbedder:
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def _project(tmp_path: Path) -> tuple[Path, RagConfig, dict]:
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "kb", root / "kb")
    shutil.copytree(ROOT / "config", root / "config")
    (root / "docs").mkdir()
    config = RagConfig.load(root)
    entry = {
        "id": "CAT-011",
        "category": "payments_refunds",
        "risk_level": "high",
        "handoff_offer": True,
        "is_mock": True,
        "answer_rendered": (
            "SAMPLE DATA — The listed fee is Rs [MOCK 999]. "
            "Check https://example.com/mock-payment before paying. "
            "I can connect a team member if needed."
        ),
    }
    return root, config, entry


@pytest.mark.parametrize(
    ("reply", "language"),
    [
        ("The fee is Rs 1,000 and the source fee is Rs [MOCK 999].", "English"),
        ("Pay here: https://invented.example/path", "English"),
        ("This is AICTE approved.", "English"),
        ("I guarantee you will be refunded.", "English"),
        ("# Fee details", "English"),
        ("x" * 601, "English"),
        ("The fee is Rs [MOCK 999].", "English"),
    ],
)
def test_verifier_rejects_unsafe_replies(
    tmp_path: Path, reply: str, language: str
) -> None:
    _, config, entry = _project(tmp_path)
    candidate = LLMReply(
        reply=reply,
        used_entry_ids=["CAT-999"] if "invented" in reply else ["CAT-011"],
        language=language,
    )
    report = verify_reply(
        candidate,
        [entry],
        {"CAT-011"},
        "English",
        config,
        SameVectorEmbedder(),
    )
    assert report.passed is False


def test_fake_invalid_json_and_timeout_fall_back_to_extractive(tmp_path: Path) -> None:
    _, config, entry = _project(tmp_path)
    provider = FakeProvider([{"wrong_field": "not a reply"}, TimeoutError("test timeout")])

    result = compose("What is the fee?", "English", [entry], provider, config, SameVectorEmbedder())

    assert result.mode == "fallback"
    assert "SAMPLE DATA" in result.reply
    assert result.verifier.fallback_used is True
    assert provider.calls[0]["user"].find("untrusted_user_message") >= 0


def test_verifier_rejects_foreign_entry_id_and_wrong_language(tmp_path: Path) -> None:
    _, config, entry = _project(tmp_path)
    foreign = verify_reply(
        LLMReply(
            reply=entry["answer_rendered"],
            used_entry_ids=["CAT-999"],
            language="English",
        ),
        [entry],
        {"CAT-011"},
        "English",
        config,
        SameVectorEmbedder(),
    )
    wrong_language = verify_reply(
        LLMReply(
            reply="SAMPLE DATA — Fee Rs [MOCK 999] hai.",
            used_entry_ids=["CAT-011"],
            language="English",
        ),
        [entry],
        {"CAT-011"},
        "English",
        config,
        SameVectorEmbedder(),
    )
    assert foreign.passed is False
    assert foreign.checks["entry_ids_subset"] is False
    assert wrong_language.passed is False
    assert wrong_language.checks["language_matches"] is False


def test_bad_fake_reply_is_rejected_then_safe_fallback_used(tmp_path: Path) -> None:
    _, config, entry = _project(tmp_path)
    provider = FakeProvider(
        [
            {
                "reply": "Your refund is guaranteed at https://example.invalid.",
                "used_entry_ids": ["CAT-011"],
                "language": "English",
            },
            TimeoutError("test retry timeout"),
        ]
    )

    result = compose("What is the fee?", "English", [entry], provider, config, SameVectorEmbedder())

    assert result.mode == "fallback"
    assert result.verifier.fallback_used is True
    assert "Rs [MOCK 999]" in result.reply
    assert result.reply.endswith("Would you like me to connect you with a team member?")
    assert result.reply.endswith("Would you like me to connect you with a team member?")
    assert result.provider_errors


def test_none_provider_is_extractive_only(tmp_path: Path) -> None:
    _, config, entry = _project(tmp_path)
    result = compose(
        "What is the fee?", "English", [entry], NoneProvider(), config, SameVectorEmbedder()
    )
    assert result.mode == "extractive"
    assert "Rs [MOCK 999]" in result.reply
    assert result.reply.endswith("Would you like me to connect you with a team member?")
    assert result.verifier.passed


def test_budget_caps_provider_timeout_and_skips_call_when_budget_is_exhausted(tmp_path: Path) -> None:
    _, config, entry = _project(tmp_path)

    class TimeoutCaptureProvider:
        name = "capture"

        def __init__(self):
            self.timeouts = []

        def generate_json(self, system, user, schema, timeout):
            self.timeouts.append(timeout)
            return {
                "reply": entry["answer_rendered"],
                "used_entry_ids": [entry["id"]],
                "language": "English",
            }, {"input_tokens": 10, "output_tokens": 10}

    provider = TimeoutCaptureProvider()
    result = compose(
        "fee amount?", "English", [entry], provider, config, SameVectorEmbedder(),
        deadline=time.perf_counter() + 2.0,
    )
    assert result.mode == "llm"
    assert len(provider.timeouts) == 1
    assert 0 < provider.timeouts[0] <= 2.0

    exhausted = TimeoutCaptureProvider()
    result = compose(
        "fee amount?", "English", [entry], exhausted, config, SameVectorEmbedder(),
        deadline=time.perf_counter() + 0.01,
    )
    assert result.mode == "fallback"
    assert exhausted.timeouts == []


def test_language_mismatch_failure_is_included_in_retry_prompt(tmp_path: Path) -> None:
    _, config, entry = _project(tmp_path)
    provider = FakeProvider([
        {
            "reply": entry["answer_rendered"],
            "used_entry_ids": [entry["id"]],
            "language": "English",
        },
        {
            "reply": "SAMPLE DATA — Fee Rs [MOCK 999] hai.",
            "used_entry_ids": [entry["id"]],
            "language": "Hinglish",
        },
    ])
    result = compose(
        "fee kitni hai", "Hinglish", [entry], provider, config, SameVectorEmbedder()
    )
    assert result.mode == "llm"
    assert result.verifier.checks["language_matches"] is True
    assert "reply language English does not match Hinglish" in provider.calls[1]["user"]


def test_gemini_falls_back_to_listed_model_on_503(monkeypatch) -> None:
    import json
    import sys
    import types

    calls = []
    google = types.ModuleType("google")
    genai = types.ModuleType("google.genai")
    sdk_types = types.ModuleType("google.genai.types")

    class ApiError(Exception):
        code = 503
        status = "UNAVAILABLE"

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = self

        def generate_content(self, model, **kwargs):
            calls.append(model)
            if model == "gemini-primary":
                raise ApiError("message deliberately not inspected")
            return types.SimpleNamespace(
                text=json.dumps({"ok": True}),
                usage_metadata=types.SimpleNamespace(prompt_token_count=3, candidates_token_count=2),
            )

    genai.Client = FakeClient
    sdk_types.HttpOptions = lambda **kwargs: kwargs
    sdk_types.HttpRetryOptions = lambda **kwargs: kwargs
    sdk_types.GenerateContentConfig = lambda **kwargs: kwargs
    google.genai = genai
    genai.types = sdk_types
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", sdk_types)

    provider = GeminiProvider("dummy-key-never-printed", "gemini-primary", fallback_models=["gemini-fallback"])
    result, usage = provider.generate_json("system", "user", {"type": "object"}, 2.0)

    assert calls == ["gemini-primary", "gemini-fallback"]
    assert result == {"ok": True}
    assert usage == {"input_tokens": 3, "output_tokens": 2}
