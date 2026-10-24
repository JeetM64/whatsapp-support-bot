from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .loader import PrepareResult, prepare_kb


def payload_for(entries: list[Any]) -> dict[str, Any]:
    serialized_entries = [entry.model_dump(mode="json") for entry in entries]
    canonical = json.dumps(
        {"entries": serialized_entries},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return {
        "schema_version": 1,
        "content_hash": digest,
        "entries": serialized_entries,
    }


def build_to_file(
    root: Path,
    *,
    output_path: Path | None = None,
) -> tuple[PrepareResult, dict[str, Any] | None]:
    result = prepare_kb(root)
    if result.errors:
        return result, None
    payload = payload_for(result.entries)
    destination = output_path or root / "kb" / "build" / "knowledge_base.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    destination.write_text(encoded, encoding="utf-8", newline="\n")
    return result, payload
