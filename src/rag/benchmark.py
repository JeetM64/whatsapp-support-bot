from __future__ import annotations

import statistics
from pathlib import Path
from typing import Iterable

from .config import RagConfig, load_dotenv
from .engine import RagEngine
from .normalize import detect_language
from .providers import NoneProvider, create_provider
from .retriever import Retriever
from .eval import load_cases


def _percentile(values: Iterable[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction + 0.999)))
    return ordered[index]


def run_benchmark(root: Path, provider_name: str, count: int = 50) -> str:
    config = RagConfig.load(root)
    cases = load_cases(root / "eval" / "retrieval_cases.csv")
    if provider_name == "none":
        selected = [case for case in cases if case["split"] == "test"][:count]
        provider = NoneProvider()
    elif provider_name == "gemini":
        selected = [
            case for case in cases
            if case["type"] == "hinglish" and case["expected_decision"] == "ANSWER"
        ][:10]
        load_dotenv(root)
        provider = create_provider(
            "gemini",
            max_tokens=int(config.provider.get("max_tokens", 256)),
            fallback_models=list(config.provider.get("fallback_models", [])),
        )
    else:
        raise ValueError("benchmark provider must be 'none' or 'gemini'")

    import time
    startup_started = time.perf_counter()
    retriever = Retriever(root, config)
    engine = RagEngine(root, provider=provider, retriever=retriever)
    startup_ms = (time.perf_counter() - startup_started) * 1000
    results = [engine.answer(case["query"]) for case in selected]
    no_llm = [result.latency_ms for result in results if result.timings_ms.get("llm_ms", 0) == 0]
    llm = [result.latency_ms for result in results if result.timings_ms.get("llm_ms", 0) > 0]
    stages = ("normalize_ms", "embed_ms", "retrieve_ms", "decide_ms", "llm_ms", "verify_ms")
    lines = [
        f"provider={provider_name} messages={len(results)} startup_warmup_ms={startup_ms:.1f}",
        "",
        "| Path | Samples | p50 ms | p95 ms | Target | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    none_p50 = statistics.median(no_llm) if no_llm else 0.0
    none_p95 = _percentile(no_llm, 0.95)
    lines.append(
        f"| Non-LLM | {len(no_llm)} | {none_p50:.1f} | {none_p95:.1f} | p50 <= 1500 | "
        f"{'PASS' if none_p50 <= 1500 else 'FAIL'} |"
    )
    llm_p50 = statistics.median(llm) if llm else 0.0
    llm_p95 = _percentile(llm, 0.95)
    llm_status = "N/A" if not llm else (
        "PASS" if llm_p50 <= 4000 and llm_p95 <= 8000 else "FAIL"
    )
    lines.append(
        f"| LLM | {len(llm)} | {llm_p50:.1f} | {llm_p95:.1f} | p50 <= 4000, p95 <= 8000 | "
        f"{llm_status} |"
    )
    lines.extend(["", "| Stage | p50 ms | p95 ms |", "|---|---:|---:|"])
    for stage in stages:
        values = [result.timings_ms.get(stage, 0.0) for result in results]
        lines.append(
            f"| {stage.removesuffix('_ms')} | {statistics.median(values):.1f} | "
            f"{_percentile(values, 0.95):.1f} |"
        )
    if provider_name == "gemini":
        hinglish_pass = sum(
            result.decision.value == "ANSWER"
            and result.mode == "llm"
            and result.verifier.passed
            and detect_language(result.reply) == "Hinglish"
            for result in results
        )
        lines.extend([
            "",
            f"Hinglish verified replies: {hinglish_pass}/{len(results)} ({hinglish_pass / max(len(results), 1):.1%}).",
        ])
        for case, result in zip(selected, results, strict=True):
            lines.append(
                f"- {case['id']}: decision={result.decision.value}, mode={result.mode}, "
                f"reply_language={detect_language(result.reply)}, verified={result.verifier.passed}, "
                f"latency_ms={result.latency_ms:.1f}, tokens={result.usage.total_tokens}."
            )
    return "\n".join(lines)
