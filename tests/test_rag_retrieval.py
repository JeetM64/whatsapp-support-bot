from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import chromadb
import numpy as np

from src.rag.config import RagConfig
from src.rag.normalize import tokenize
from src.rag.retriever import Retriever

ROOT = Path(__file__).resolve().parents[1]


def copy_project(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "kb", root / "kb")
    shutil.copytree(ROOT / "config", root / "config")
    (root / "docs").mkdir()
    return root


class StableFakeEmbedder:
    def __init__(self, root: Path) -> None:
        self.lexicon = root / "kb" / "lexicon.yaml"

    def encode(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            vector = np.zeros(64, dtype=np.float32)
            for token in set(tokenize(text, self.lexicon)):
                index = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:2], "little") % 64
                vector[index] += 1
            norm = float(np.linalg.norm(vector))
            if norm:
                vector /= norm
            results.append(vector.tolist())
        return results


def test_fusion_order_is_deterministic(tmp_path: Path) -> None:
    root = copy_project(tmp_path)
    config = RagConfig.load(root)
    retriever = Retriever(root, config, embedder=StableFakeEmbedder(root), use_model_cache=False)

    first = retriever.retrieve("fee kitni hai")
    second = retriever.retrieve("fee kitni hai")

    assert [candidate.id for candidate in first.candidates] == [
        candidate.id for candidate in second.candidates
    ]
    assert [candidate.rrf_score for candidate in first.candidates] == [
        candidate.rrf_score for candidate in second.candidates
    ]
    assert first.candidates[0].id == "CAT-011"


def test_document_index_contains_base_and_each_variant(tmp_path: Path) -> None:
    root = copy_project(tmp_path)
    config = RagConfig.load(root)
    retriever = Retriever(root, config, embedder=StableFakeEmbedder(root), use_model_cache=False)

    retriever.retrieve("certificate milestone")

    client = chromadb.PersistentClient(
        path=str(config.chroma_path),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )
    collection = client.get_collection(retriever.collection_name)
    assert collection.count() == len(retriever.documents)
    assert any(document["kind"] == "variant" for document in retriever.documents)


def test_kb_hash_change_gets_a_new_collection(tmp_path: Path) -> None:
    root = copy_project(tmp_path)
    config = RagConfig.load(root)
    first = Retriever(root, config, embedder=StableFakeEmbedder(root), use_model_cache=False)
    first.retrieve("fee kitni hai")
    first_collection = first.collection_name

    kb_path = root / "kb" / "build" / "knowledge_base.json"
    payload = json.loads(kb_path.read_text(encoding="utf-8"))
    payload["content_hash"] = "new-version-for-test"
    kb_path.write_text(json.dumps(payload), encoding="utf-8")
    second = Retriever(root, config, embedder=StableFakeEmbedder(root), use_model_cache=False)
    second.retrieve("fee kitni hai")

    assert second.collection_name != first_collection
    collections = chromadb.PersistentClient(
        path=str(config.chroma_path),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    ).list_collections()
    assert first_collection in {item.name for item in collections}
    assert second.collection_name in {item.name for item in collections}


def test_missing_model_cache_degrades_to_lexical_only(tmp_path: Path) -> None:
    root = copy_project(tmp_path)
    retriever = Retriever(root, embedder=None, use_model_cache=False)

    result = retriever.retrieve("fee kitni hai")

    assert result.degraded is True
    assert result.semantic_available is False
    assert result.candidates[0].id == "CAT-011"
