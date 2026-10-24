from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.rag.composer import compose
from src.rag.config import RagConfig
from src.rag.models import LLMReply
from src.rag.providers import FakeProvider, NoneProvider
from src.rag.verifier import verify_reply

ROOT = Path(__file__).resolve().parents[1]


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
    assert result.reply == entry["answer_rendered"]
    assert result.provider_errors


def test_none_provider_is_extractive_only(tmp_path: Path) -> None:
    _, config, entry = _project(tmp_path)
    result = compose(
        "What is the fee?", "English", [entry], NoneProvider(), config, SameVectorEmbedder()
    )
    assert result.mode == "extractive"
    assert result.reply == entry["answer_rendered"]
    assert result.verifier.passed
