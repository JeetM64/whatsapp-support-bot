from pathlib import Path

from src.rag.lexicon import load_lexicon

ROOT = Path(__file__).resolve().parents[1]


def test_lexicon_has_at_least_eighty_aliases_and_longest_phrases_first() -> None:
    aliases = load_lexicon(str((ROOT / "kb" / "lexicon.yaml").resolve()))
    assert len(aliases) >= 80
    assert aliases == tuple(sorted(aliases, key=lambda pair: (-len(pair[0]), pair[0], pair[1])))
    assert ("kitni", "fee-quantity") in aliases
    assert ("praman patra", "certificate") in aliases
