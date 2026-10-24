from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from .config import RagConfig
from .embeddings import Embedder, FastEmbedder
from .models import Candidate
from .normalize import tokenize


class ChromaStorageBusy(RuntimeError):
    """A clear, non-destructive error for a locked or unavailable local index."""


@dataclass
class RetrievalOutput:
    candidates: list[Candidate]
    confidence: float
    margin: float
    degraded: bool
    lexical_agreement: bool
    semantic_available: bool
    query_token_count: int


def load_kb(root: Path) -> tuple[dict[str, dict[str, Any]], str]:
    path = root / "kb" / "build" / "knowledge_base.json"
    if not path.exists():
        raise FileNotFoundError("Generated KB not found. Run: .\\.venv\\Scripts\\python.exe -m src.kb build")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    entries = payload.get("entries", [])
    if not entries or not payload.get("content_hash"):
        raise ValueError("Generated KB is empty or has no content hash")
    return {entry["id"]: entry for entry in entries}, str(payload["content_hash"])


def _source_documents(entries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for entry_id in sorted(entries):
        entry = entries[entry_id]
        question = str(entry["question"])
        variants = list(entry.get("hinglish_variants", []))
        keywords = list(entry.get("keywords", []))
        documents.append(
            {
                "doc_id": f"{entry_id}::base",
                "entry_id": entry_id,
                "category": entry["category"],
                "kind": "base",
                "text": " ".join([question, *variants, *keywords]),
            }
        )
        for index, variant in enumerate(variants):
            documents.append(
                {
                    "doc_id": f"{entry_id}::variant-{index:02d}",
                    "entry_id": entry_id,
                    "category": entry["category"],
                    "kind": "variant",
                    "text": str(variant),
                }
            )
    return documents


def _bm25_scores(
    query_tokens: list[str],
    documents: list[dict[str, Any]],
    config: RagConfig,
) -> tuple[dict[str, float], dict[str, float]]:
    tokenized = [
        tokenize(str(document["text"]), config.root / "kb" / "lexicon.yaml")
        for document in documents
    ]
    if not query_tokens or not tokenized:
        return {}, {}
    lengths = [len(tokens) for tokens in tokenized]
    average_length = sum(lengths) / max(len(lengths), 1)
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))
    n_docs = len(tokenized)
    k1 = float(config.retrieval.get("bm25_k1", 1.5))
    b = float(config.retrieval.get("bm25_b", 0.75))
    doc_scores: list[float] = []
    query_set = set(query_tokens)
    for tokens, length in zip(tokenized, lengths, strict=True):
        term_frequency = Counter(tokens)
        score = 0.0
        for term in query_set:
            frequency = term_frequency.get(term, 0)
            if not frequency:
                continue
            idf = math.log(1.0 + (n_docs - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            denominator = frequency + k1 * (1.0 - b + b * length / max(average_length, 1.0))
            score += idf * frequency * (k1 + 1.0) / denominator
        doc_scores.append(score)

    scores: dict[str, float] = defaultdict(float)
    overlap: dict[str, float] = defaultdict(float)
    for document, tokens, score in zip(documents, tokenized, doc_scores, strict=True):
        entry_id = str(document["entry_id"])
        scores[entry_id] = max(scores[entry_id], score)
        common = len(query_set.intersection(tokens)) / max(len(query_set), 1)
        overlap[entry_id] = max(overlap[entry_id], common)
    return dict(scores), dict(overlap)


class Retriever:
    def __init__(
        self,
        root: Path,
        config: RagConfig | None = None,
        *,
        embedder: Embedder | None = None,
        use_model_cache: bool = True,
    ) -> None:
        self.root = root.resolve()
        self.config = config or RagConfig.load(self.root)
        self.entries, self.kb_hash = load_kb(self.root)
        self.documents = _source_documents(self.entries)
        self._provided_embedder = embedder is not None
        self.embedder = embedder
        if self.embedder is None and use_model_cache:
            try:
                self.embedder = FastEmbedder(self.config, allow_download=False)
            except Exception:
                self.embedder = None
        self.degraded = self.embedder is None

    @property
    def collection_name(self) -> str:
        return f"kb_{self.kb_hash[:24]}"

    def _collection(self) -> Any:
        try:
            client = chromadb.PersistentClient(
                path=str(self.config.chroma_path),
                settings=Settings(anonymized_telemetry=False),
            )
            collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "kb_content_hash": self.kb_hash,
                    "embedding_model": self.config.embedding_model,
                    "hnsw:space": "cosine",
                },
            )
            expected = len(self.documents)
            present = collection.count()
            if present not in {0, expected}:
                client.delete_collection(name=self.collection_name)
                collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={
                        "kb_content_hash": self.kb_hash,
                        "embedding_model": self.config.embedding_model,
                        "hnsw:space": "cosine",
                    },
                )
                present = 0
            if present == 0:
                if self.embedder is None:
                    return None
                batch_size = int(self.config.retrieval.get("index_batch_size", 64))
                for start in range(0, expected, batch_size):
                    batch = self.documents[start : start + batch_size]
                    vectors = self.embedder.encode([item["text"] for item in batch])
                    collection.add(
                        ids=[item["doc_id"] for item in batch],
                        documents=[item["text"] for item in batch],
                        embeddings=vectors,
                        metadatas=[
                            {
                                "entry_id": item["entry_id"],
                                "category": item["category"],
                                "kind": item["kind"],
                            }
                            for item in batch
                        ],
                    )
            return collection
        except (PermissionError, OSError, sqlite3.OperationalError) as exc:
            raise ChromaStorageBusy(
                "ChromaDB storage is locked or unavailable. Close any other process using "
                "chroma_db and retry; the index was not cleared."
            ) from exc
        except Exception as exc:
            if "lock" in str(exc).casefold() or "readonly" in str(exc).casefold():
                raise ChromaStorageBusy(
                    "ChromaDB storage is locked or read-only. Close any other process using "
                    "chroma_db and retry; the index was not cleared."
                ) from exc
            raise

    def retrieve(self, query: str) -> RetrievalOutput:
        lexicon_path = self.root / "kb" / "lexicon.yaml"
        query_tokens = tokenize(query, lexicon_path)
        lexical_scores, lexical_overlaps = _bm25_scores(query_tokens, self.documents, self.config)
        lexical_ranked = sorted(
            lexical_scores,
            key=lambda entry_id: (-lexical_scores[entry_id], entry_id),
        )
        semantic_scores: dict[str, float] = {}
        semantic_ranked: list[str] = []
        collection = None
        if self.embedder is not None:
            collection = self._collection()
        if collection is not None and self.embedder is not None:
            try:
                query_vector = self.embedder.encode([query])[0]
                result = collection.query(
                    query_embeddings=[query_vector],
                    n_results=min(max(int(self.config.retrieval["top_k"]) * 4, 24), len(self.documents)),
                    include=["distances", "metadatas"],
                )
                best_by_entry: dict[str, float] = {}
                ids = result.get("ids", [[]])[0]
                distances = result.get("distances", [[]])[0]
                metadatas = result.get("metadatas", [[]])[0]
                for doc_id, distance, metadata in zip(ids, distances, metadatas, strict=True):
                    entry_id = str(metadata["entry_id"])
                    similarity = max(0.0, min(1.0, 1.0 - float(distance)))
                    best_by_entry[entry_id] = max(best_by_entry.get(entry_id, 0.0), similarity)
                semantic_scores = best_by_entry
                semantic_ranked = sorted(
                    semantic_scores,
                    key=lambda entry_id: (-semantic_scores[entry_id], entry_id),
                )
            except (PermissionError, OSError, sqlite3.OperationalError) as exc:
                raise ChromaStorageBusy(
                    "ChromaDB storage is locked or unavailable. Close any other process using "
                    "chroma_db and retry; the index was not cleared."
                ) from exc

        k = int(self.config.retrieval.get("rrf_k", 60))
        sem_rank = {entry_id: rank for rank, entry_id in enumerate(semantic_ranked, start=1)}
        lex_rank = {entry_id: rank for rank, entry_id in enumerate(lexical_ranked, start=1)}
        ids = set(sem_rank) | set(lex_rank)
        rrf_scores = {
            entry_id: (
                (1.0 / (k + sem_rank[entry_id]) if entry_id in sem_rank else 0.0)
                + (1.0 / (k + lex_rank[entry_id]) if entry_id in lex_rank else 0.0)
            )
            for entry_id in ids
        }
        ordered = sorted(ids, key=lambda entry_id: (-rrf_scores[entry_id], entry_id))
        top_k = int(self.config.retrieval["top_k"])
        semantic_available = bool(semantic_scores)
        def evidence(entry_id: str) -> float:
            semantic = semantic_scores.get(entry_id, 0.0)
            lexical = lexical_overlaps.get(entry_id, 0.0)
            return 0.55 * semantic + 0.30 * lexical if semantic_available else 0.85 * lexical

        top_evidence = evidence(ordered[0]) if ordered else 0.0
        second_evidence = evidence(ordered[1]) if len(ordered) > 1 else 0.0
        margin = max(0.0, (top_evidence - second_evidence) / max(top_evidence, 1e-9))
        candidates: list[Candidate] = []
        for index, entry_id in enumerate(ordered[:top_k]):
            semantic = semantic_scores.get(entry_id, 0.0)
            lexical = lexical_overlaps.get(entry_id, 0.0)
            candidate_margin = margin if index == 0 else 0.0
            if semantic_available:
                confidence = 0.55 * semantic + 0.30 * lexical + 0.15 * candidate_margin
            else:
                confidence = 0.85 * lexical + 0.15 * candidate_margin
            entry = self.entries[entry_id]
            candidates.append(
                Candidate(
                    id=entry_id,
                    category=str(entry["category"]),
                    is_mock=bool(entry["is_mock"]),
                    rrf_score=rrf_scores[entry_id],
                    semantic_score=semantic,
                    lexical_score=lexical,
                    confidence=max(0.0, min(1.0, confidence)),
                )
            )
        confidence = candidates[0].confidence if candidates else 0.0
        best_lexical = candidates[0].lexical_score if candidates else 0.0
        min_overlap = float(self.config.retrieval.get("min_lexical_overlap", 0.10))
        lexical_agreement = best_lexical >= min_overlap
        return RetrievalOutput(
            candidates=candidates,
            confidence=confidence,
            margin=margin,
            degraded=self.degraded,
            lexical_agreement=lexical_agreement,
            semantic_available=semantic_available,
            query_token_count=len(set(query_tokens)),
        )
