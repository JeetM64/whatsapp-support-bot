from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .lexicon import load_lexicon

TOKEN_RE = re.compile(r"[^\W_]+(?:-[^\W_]+)*", re.UNICODE)
HINGLISH_MARKERS = {
    "hai", "hain", "kya", "nahi", "nhi", "paisa", "paise", "kaise", "kitna",
    "kitni", "milega", "mila", "karu", "chahiye", "karo", "mera", "meri",
}


def normalize_text(text: str, lexicon_path: Path) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"([^\W_])\1{2,}", r"\1", normalized, flags=re.UNICODE)

    aliases = load_lexicon(str(lexicon_path.resolve()))
    replacements = {alias: canonical for alias, canonical in aliases}
    alternatives = "|".join(re.escape(alias) for alias, _ in aliases)
    pattern = re.compile(r"(?<![\w-])(" + alternatives + r")(?![\w-])", re.UNICODE)
    normalized = pattern.sub(
        lambda match: f" {replacements[match.group(0)]} ",
        normalized,
    )

    kept: list[str] = []
    for character in normalized:
        category = unicodedata.category(character)
        if character.isspace() or category[0] in {"L", "N", "M"} or character == "-":
            kept.append(character)
        else:
            kept.append(" ")
    normalized = re.sub(r"\s+", " ", "".join(kept)).strip()
    return normalized


def tokenize(text: str, lexicon_path: Path) -> list[str]:
    return TOKEN_RE.findall(normalize_text(text, lexicon_path))


def detect_language(text: str, lexicon_path: Path | None = None) -> str:
    if any("\u0900" <= character <= "\u097f" for character in text):
        return "Hindi"
    tokens = set(TOKEN_RE.findall(unicodedata.normalize("NFKC", text).casefold()))
    if tokens & HINGLISH_MARKERS:
        return "Hinglish"
    return "English"
