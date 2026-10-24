from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class RagConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    embedding: dict[str, Any]
    retrieval: dict[str, Any]
    thresholds: dict[str, float]
    decision: dict[str, Any]
    provider: dict[str, Any]
    pricing: dict[str, Any]
    evaluation: dict[str, Any]
    root: Path

    @property
    def embedding_model(self) -> str:
        return str(self.embedding["model_name"])

    @property
    def embedding_cache(self) -> Path:
        return (self.root / str(self.embedding["cache_dir"])).resolve()

    @property
    def chroma_path(self) -> Path:
        return self.root / "chroma_db"

    @property
    def sample_label_enabled(self) -> bool:
        return bool(self.decision.get("show_sample_label", True))

    @classmethod
    def load(cls, root: Path | None = None) -> "RagConfig":
        project_root = (root or Path.cwd()).resolve()
        path = project_root / "config" / "rag.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
        data["root"] = project_root
        return cls.model_validate(data)


def load_dotenv(root: Path) -> None:
    """Load simple KEY=VALUE pairs without ever logging their values."""
    path = root / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        name = name.strip()
        value = value.strip().strip("\"'")
        if name and name not in os.environ:
            os.environ[name] = value
