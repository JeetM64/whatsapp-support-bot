from __future__ import annotations

import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml


@lru_cache(maxsize=8)
def load_lexicon(path_string: str) -> tuple[tuple[str, str], ...]:
    """Load editable Roman-Hinglish aliases, longest phrases first."""
    path = Path(path_string)
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    terms = data.get("terms", {})
    aliases: list[tuple[str, str]] = []
    for canonical, variants in terms.items():
        for variant in variants:
            alias = unicodedata.normalize("NFKC", str(variant)).casefold().strip()
            if alias:
                aliases.append((alias, str(canonical)))
    aliases.sort(key=lambda pair: (-len(pair[0]), pair[0], pair[1]))
    return tuple(aliases)
