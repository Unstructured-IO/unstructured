#!/usr/bin/env python3
"""Benchmark sequential versus batched spaCy-backed text classification.

This benchmark generates unique, NLP-heavy sentences and classifies each one through
Unstructured's existing ``element_from_text`` function. The sequential mode allows the
tokenization helpers to invoke spaCy individually, while the batched mode makes the same
classifier calls inside ``batch_process_texts``, which precomputes documents with ``nlp.pipe``.

The spaCy model is loaded before timing, and sentence, word, and POS caches are cleared before
every sample. This isolates text-processing throughput from model startup and cache reuse.
Execution order alternates between modes to reduce ordering bias. A SHA-256 fingerprint over
element category and text verifies exact classification parity for the generated corpus.

Examples:
  uv run --no-sync python scripts/performance/benchmark_text_classification.py

  uv run --no-sync python scripts/performance/benchmark_text_classification.py \
    --count 10000 --batch-size 256 --iterations 3

  uv run --no-sync python scripts/performance/benchmark_text_classification.py \
    --workload all --counts 1,4,16,40,100,1000 --context-size 64 --iterations 5

Workloads can be NLP-heavy, cheap to classify without NLP, or mixed. Multiple corpus sizes and
bounded, page-like contexts can be exercised in one invocation. Every timing sample is reported
along with its median so variance remains visible. The benchmark does not measure spaCy startup,
PDF extraction, layout processing, metadata generation, or warm tokenizer-cache hits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from collections import Counter
from collections.abc import Callable

from unstructured.nlp import tokenize
from unstructured.partition.text import (
    _element_from_text_with_nlp,
    _element_from_text_without_nlp,
    element_from_text,
)


def _positive_int(value: str) -> int:
    """Parse a command-line value that must be greater than zero."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be greater than zero")
    return parsed


def _comma_separated_positive_ints(value: str) -> tuple[int, ...]:
    """Parse a comma-separated sequence of positive integers."""
    values = tuple(_positive_int(item.strip()) for item in value.split(","))
    if not values:
        raise argparse.ArgumentTypeError("at least one integer is required")
    return values


def _nlp_heavy_text(index: int) -> str:
    return f"Record {index} describes how the parser processes documents efficiently."


def _cheap_text(index: int) -> str:
    # Numeric text exits narrative and title detection before a tokenizer is needed.
    return str(10_000_000 + index)


def _texts(count: int, workload: str) -> list[str]:
    text_factory: Callable[[int], str]
    if workload == "nlp-heavy":
        text_factory = _nlp_heavy_text
    elif workload == "cheap":
        text_factory = _cheap_text
    elif workload == "mixed":
        return [
            _nlp_heavy_text(index) if index % 2 == 0 else _cheap_text(index)
            for index in range(count)
        ]
    else:
        raise ValueError(f"unknown workload: {workload}")
    return [text_factory(index) for index in range(count)]


def _clear_caches() -> None:
    tokenize._tokenize_for_cache.cache_clear()
    tokenize.word_tokenize.cache_clear()
    tokenize.pos_tag.cache_clear()


def _run(
    texts: list[str],
    *,
    batch_size: int | None,
    context_size: int,
) -> tuple[float, str, Counter[str]]:
    _clear_caches()
    started = time.perf_counter()
    if batch_size is None:
        elements = [element_from_text(text) for text in texts]
    else:
        classified_elements = [_element_from_text_without_nlp(text) for text in texts]
        nlp_indices = [
            index for index, element in enumerate(classified_elements) if element is None
        ]
        for start in range(0, len(nlp_indices), context_size):
            group_indices = nlp_indices[start : start + context_size]
            with tokenize.batch_process_texts(
                (texts[index] for index in group_indices),
                batch_size=batch_size,
            ):
                for index in group_indices:
                    classified_elements[index] = _element_from_text_with_nlp(texts[index])
        if any(element is None for element in classified_elements):
            raise AssertionError("benchmark text was not classified")
        elements = [element for element in classified_elements if element is not None]
    elapsed = time.perf_counter() - started
    fingerprint = hashlib.sha256(
        json.dumps(
            [(element.category, element.text) for element in elements],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return elapsed, fingerprint, Counter(element.category for element in elements)


def _benchmark(
    *,
    count: int,
    workload: str,
    batch_size: int,
    context_size: int,
    iterations: int,
) -> dict[str, object]:
    texts = _texts(count, workload)
    timings: dict[str, list[float]] = {"sequential": [], "batched": []}
    fingerprints: set[str] = set()
    category_counts: set[tuple[tuple[str, int], ...]] = set()

    for iteration in range(iterations):
        modes = (None, batch_size) if iteration % 2 == 0 else (batch_size, None)
        for selected_batch_size in modes:
            elapsed, fingerprint, categories = _run(
                texts,
                batch_size=selected_batch_size,
                context_size=context_size,
            )
            mode = "sequential" if selected_batch_size is None else "batched"
            timings[mode].append(elapsed)
            fingerprints.add(fingerprint)
            category_counts.add(tuple(sorted(categories.items())))

    if len(fingerprints) != 1 or len(category_counts) != 1:
        raise RuntimeError("sequential and batched element outputs differ")

    sequential = statistics.median(timings["sequential"])
    batched = statistics.median(timings["batched"])
    return {
        "workload": workload,
        "unique_texts": len(texts),
        "iterations": iterations,
        "batch_size": batch_size,
        "context_size": context_size,
        "sequential_seconds": [round(value, 6) for value in timings["sequential"]],
        "batched_seconds": [round(value, 6) for value in timings["batched"]],
        "sequential_median_seconds": round(sequential, 6),
        "batched_median_seconds": round(batched, 6),
        "speedup": round(sequential / batched, 2),
        "category_counts": dict(category_counts.pop()),
        "output_fingerprint": fingerprints.pop(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=_positive_int, default=10_000)
    parser.add_argument(
        "--counts",
        type=_comma_separated_positive_ints,
        help="comma-separated corpus sizes; overrides --count",
    )
    parser.add_argument(
        "--workload",
        choices=("nlp-heavy", "cheap", "mixed", "all"),
        default="nlp-heavy",
    )
    parser.add_argument("--batch-size", type=_positive_int, default=256)
    parser.add_argument(
        "--context-size",
        type=_positive_int,
        help="maximum texts per batch context; defaults to the corpus size",
    )
    parser.add_argument("--iterations", type=_positive_int, default=3)
    args = parser.parse_args()

    tokenize._get_nlp()  # Exclude model-loading time from both measurements.
    counts = args.counts or (args.count,)
    workloads = ("nlp-heavy", "cheap", "mixed") if args.workload == "all" else (args.workload,)
    benchmarks = [
        _benchmark(
            count=count,
            workload=workload,
            batch_size=args.batch_size,
            context_size=args.context_size or count,
            iterations=args.iterations,
        )
        for workload in workloads
        for count in counts
    ]
    output: object = benchmarks[0] if len(benchmarks) == 1 else {"benchmarks": benchmarks}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
