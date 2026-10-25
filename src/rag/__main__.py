from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path

from .config import RagConfig, load_dotenv
from .benchmark import run_benchmark
from .decision import decide
from .embeddings import FastEmbedder, cosine_similarity, supported_multilingual_models
from .engine import RagEngine
from .eval import run_eval
from .normalize import detect_language
from .providers import FakeProvider, NoneProvider, create_provider
from .retriever import Retriever, load_kb


def _demo_fake_provider() -> FakeProvider:
    def bad_reply(system, user, schema, timeout):
        payload = json.loads(user)
        entry_id = payload["selected_entries"][0]["id"]
        return {
            "reply": "Your refund is guaranteed at https://example.invalid. I promise you will get a refund.",
            "used_entry_ids": [entry_id],
            "language": payload["detected_language"],
        }

    return FakeProvider(
        [
            bad_reply,
            TimeoutError("scripted retry timeout after the intentionally unsafe first reply"),
        ]
    )


def _provider(name: str | None, root: Path):
    load_dotenv(root)
    if name == "fake":
        return _demo_fake_provider()
    if name == "none":
        return NoneProvider()
    return create_provider(name)


def _print_result(result) -> None:
    print(
        f"decision={result.decision.value} reason={result.reason_code} "
        f"confidence={result.confidence:.3f} mode={result.mode} degraded={result.degraded}"
    )
    print(
        f"detected_language={result.language} reply_language={detect_language(result.reply)} "
        f"latency_ms={result.latency_ms:.1f}"
    )
    print(f"reply={result.reply}")
    print(
        "entries="
        + (", ".join(f"{entry.id}:{entry.category}:mock={entry.is_mock}" for entry in result.entries) or "NONE")
    )
    print(
        f"verifier_passed={result.verifier.passed} "
        f"fallback_used={result.verifier.fallback_used} checks={result.verifier.checks}"
    )
    if result.verifier.failures:
        print("verifier_failures=" + " | ".join(result.verifier.failures))
    print(
        f"usage={result.usage.model_dump()} estimated_cost_usd={result.estimated_cost_usd}"
    )
    print("timings_ms=" + json.dumps(result.timings_ms, sort_keys=True))


def warmup(root: Path) -> int:
    config = RagConfig.load(root)
    supported = supported_multilingual_models()
    chosen = next(
        (item for item in supported if item.get("model") == config.embedding_model),
        None,
    )
    if chosen is None:
        print(
            f"Configured multilingual model is not in FastEmbed {config.embedding['fastembed_version']} registry.",
            file=sys.stderr,
        )
        return 1
    actual_version = importlib.metadata.version("fastembed")
    if actual_version != str(config.embedding["fastembed_version"]):
        print(f"FastEmbed version mismatch: config={config.embedding['fastembed_version']} installed={actual_version}")
        return 1

    print(f"FastEmbed version: {actual_version}")
    print(f"Chosen model: {chosen['model']}")
    print(f"Description: {chosen['description']}")
    print(f"Dimensions: {chosen['dim']}; model weight size: {chosen['size_in_GB']} GB")
    embedder = FastEmbedder.warmup(config)
    entries, _ = load_kb(root)
    examples = [
        ("fee kitni hai", "CAT-011", "CAT-027"),
        ("btech web dev internship ka certificate milega kya", "CAT-017", "CAT-030"),
        ("payment cut gaya par access nahi aaya", "CAT-013", "CAT-019"),
        ("password reset kaise karu", "CAT-022", "CAT-015"),
        ("next batch kab start hoga", "CAT-009", "CAT-011"),
    ]
    texts: list[str] = []
    for query, positive_id, negative_id in examples:
        texts.extend(
            [
                query,
                str(entries[positive_id]["question"]),
                str(entries[negative_id]["question"]),
            ]
        )
    vectors = embedder.encode(texts)
    print("Hinglish similarity smoke examples (query → expected KB question / unrelated question):")
    order_checks = []
    for index, (query, positive_id, negative_id) in enumerate(examples):
        query_vector, positive_vector, negative_vector = vectors[index * 3 : index * 3 + 3]
        positive = cosine_similarity(query_vector, positive_vector)
        negative = cosine_similarity(query_vector, negative_vector)
        passed = positive > negative
        order_checks.append(passed)
        print(
            f"{index + 1}. {query!r} → {positive_id} {positive:.3f} / "
            f"{negative_id} {negative:.3f} ({'PASS' if passed else 'CHECK'})"
        )
    print(f"Warmup complete; cache: {config.embedding_cache}")
    print(f"Relative-order checks: {sum(order_checks)}/5")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m src.rag")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("warmup")
    ask_parser = subparsers.add_parser("ask")
    ask_parser.add_argument("message")
    ask_parser.add_argument("--provider", choices=("none", "fake", "gemini", "anthropic"))
    eval_parser = subparsers.add_parser("eval")
    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("--provider", choices=("none", "gemini"), default="none")
    benchmark_parser.add_argument("--count", type=int, default=50)
    explain_parser = subparsers.add_parser("explain")
    explain_parser.add_argument("message")
    explain_parser.add_argument("--provider", choices=("none", "fake", "gemini", "anthropic"))
    args = parser.parse_args()
    root = Path.cwd().resolve()

    if args.command == "warmup":
        try:
            return warmup(root)
        except Exception as exc:
            print(f"Warmup failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    if args.command == "eval":
        try:
            config = RagConfig.load(root)
            retriever = Retriever(root, config)
            if retriever.degraded:
                print("WARNING: multilingual model is not cached; evaluation is lexical-only.")
            report, metrics = run_eval(root, retriever, config)
            print(report)
            print("Saved docs/rag_eval.md")
            print(
                "TEST_TARGETS "
                f"top3={'PASS' if metrics['top3'] >= 0.95 else 'FAIL'} "
                f"false_accept={'PASS' if metrics['false_accept_rate'] == 0 else 'FAIL'} "
                f"injection={'PASS' if metrics['injection_pass'] == 1 else 'FAIL'}"
            )
            return 0
        except Exception as exc:
            print(f"Evaluation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    if args.command == "benchmark":
        try:
            print(run_benchmark(root, args.provider, args.count))
            return 0
        except Exception as exc:
            print(f"Benchmark failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    provider = _provider(args.provider, root)
    engine = RagEngine(root, provider=provider)
    if args.command == "ask":
        result = engine.answer(args.message)
        _print_result(result)
        return 0

    if engine.retriever is not None:
        retrieval = engine.retriever.retrieve(args.message)
        decision = decide(args.message, retrieval, engine.retriever.entries, engine.config)
        print(
            f"decision={decision.decision.value} reason={decision.reason_code} "
            f"confidence={decision.confidence:.3f} margin={retrieval.margin:.3f} "
            f"degraded={retrieval.degraded}"
        )
        for candidate in retrieval.candidates:
            print(
                f"candidate={candidate.id} category={candidate.category} "
                f"rrf={candidate.rrf_score:.6f} semantic={candidate.semantic_score:.3f} "
                f"lexical={candidate.lexical_score:.3f} confidence={candidate.confidence:.3f}"
            )
    result = engine.answer(args.message)
    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
