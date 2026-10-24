from __future__ import annotations

from pathlib import Path
from typing import Iterable, Protocol

import numpy as np
from fastembed import TextEmbedding

from .config import RagConfig


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedder:
    def __init__(self, config: RagConfig, *, allow_download: bool = False) -> None:
        self.config = config
        self.config.embedding_cache.mkdir(parents=True, exist_ok=True)
        self.model = TextEmbedding(
            model_name=config.embedding_model,
            cache_dir=str(config.embedding_cache),
            lazy_load=True,
            local_files_only=not allow_download,
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.embed(texts)
        return [np.asarray(vector, dtype=np.float32).tolist() for vector in vectors]

    @classmethod
    def warmup(cls, config: RagConfig) -> "FastEmbedder":
        embedder = cls(config, allow_download=True)
        sample_vectors = embedder.encode(["fee kitni hai", "certificate milega kya"])
        if len(sample_vectors) != 2 or not all(sample_vectors):
            raise RuntimeError("FastEmbed warmup returned empty embeddings")
        return embedder


def supported_multilingual_models() -> list[dict[str, object]]:
    return [
        item
        for item in TextEmbedding.list_supported_models()
        if "multilingual" in str(item.get("description", "")).casefold()
    ]


def cosine_similarity(first: Iterable[float], second: Iterable[float]) -> float:
    left = np.asarray(list(first), dtype=np.float32)
    right = np.asarray(list(second), dtype=np.float32)
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0:
        return 0.0
    return float(np.dot(left, right) / denominator)
