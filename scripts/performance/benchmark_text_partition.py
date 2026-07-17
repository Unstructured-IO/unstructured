#!/usr/bin/env python3
"""Benchmark text-heavy partition paths while excluding NLP result-cache hits.

This benchmark is aimed at changes to the text-classification path. It keeps the
spaCy model loaded, but clears cached tokenization/classification results before
each iteration. This models processing new document text without folding model
startup time into every sample.

The output fingerprint covers every element's concrete type and text. Pass a
baseline result with ``--compare`` to verify exact output parity and report the
speedup.

Examples:
    # Run on upstream/main, then on the candidate branch.
    uv run --no-sync python scripts/performance/benchmark_text_partition.py /tmp/main.json
    uv run --no-sync python scripts/performance/benchmark_text_partition.py \
        /tmp/candidate.json --compare /tmp/main.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from unstructured.documents.elements import Element
from unstructured.nlp import tokenize
from unstructured.partition.auto import partition

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_INPUTS = (
    REPO_ROOT / "example-docs/book-war-and-peace-1225p.txt",
    REPO_ROOT / "example-docs/example-10k-230p.html",
    REPO_ROOT / "example-docs/handbook-872p.docx",
    REPO_ROOT / "example-docs/science-exploration-369p.pptx",
)
DEFAULT_WARMUP_INPUT = REPO_ROOT / "example-docs/book-war-and-peace-1p.txt"


def clear_nlp_result_caches() -> None:
    """Clear per-text results without unloading the spaCy model."""
    tokenize.word_tokenize.cache_clear()
    tokenize.pos_tag.cache_clear()
    tokenize._tokenize_for_cache.cache_clear()


def fingerprint(elements: Sequence[Element]) -> tuple[str, dict[str, int]]:
    """Return a stable digest and type counts for exact classification/text output."""
    output = [(type(element).__name__, element.text) for element in elements]
    encoded = json.dumps(output, ensure_ascii=False, separators=(",", ":")).encode()
    type_counts = dict(sorted(Counter(element_type for element_type, _ in output).items()))
    return hashlib.sha256(encoded).hexdigest(), type_counts


def display_path(path: Path) -> str:
    """Return a repository-relative path when possible."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run_document(input_path: Path, iterations: int) -> dict[str, Any]:
    """Measure one document and ensure its output is stable across iterations."""
    samples: list[float] = []
    expected_fingerprint: str | None = None
    element_count = 0
    type_counts: dict[str, int] = {}

    for _ in range(iterations):
        clear_nlp_result_caches()
        started = time.perf_counter()
        elements = partition(filename=str(input_path), strategy="fast")
        samples.append(time.perf_counter() - started)

        output_fingerprint, current_type_counts = fingerprint(elements)
        if expected_fingerprint is not None and output_fingerprint != expected_fingerprint:
            raise RuntimeError("partition output changed between benchmark iterations")
        expected_fingerprint = output_fingerprint
        element_count = len(elements)
        type_counts = current_type_counts

    return {
        "seconds": {
            "samples": [round(sample, 6) for sample in samples],
            "median": round(statistics.median(samples), 6),
            "mean": round(statistics.fmean(samples), 6),
            "min": round(min(samples), 6),
            "max": round(max(samples), 6),
        },
        "output": {
            "sha256": expected_fingerprint,
            "element_count": element_count,
            "type_counts": type_counts,
        },
    }


def run_benchmark(
    input_paths: Sequence[Path], warmup_path: Path, iterations: int
) -> dict[str, Any]:
    """Warm the model once, then benchmark every document in the representative matrix."""
    partition(filename=str(warmup_path), strategy="fast")
    clear_nlp_result_caches()

    documents = {
        display_path(input_path): run_document(input_path, iterations) for input_path in input_paths
    }
    median_total = sum(document["seconds"]["median"] for document in documents.values())
    return {
        "iterations": iterations,
        "documents": documents,
        "summary": {"median_total_seconds": round(median_total, 6)},
    }


def compare_results(current: dict[str, Any], baseline_path: Path) -> None:
    """Verify every document's output and print per-document and aggregate speedups."""
    baseline = json.loads(baseline_path.read_text())
    baseline_documents = baseline.get("documents", {})
    current_documents = current["documents"]
    if current_documents.keys() != baseline_documents.keys():
        raise SystemExit("ERROR: candidate and baseline document sets differ")

    print("\nComparison:")
    for name, document in current_documents.items():
        baseline_document = baseline_documents[name]
        if document["output"] != baseline_document.get("output"):
            raise SystemExit(f"ERROR: candidate output differs for {name}")

        baseline_median = baseline_document["seconds"]["median"]
        current_median = document["seconds"]["median"]
        speedup = baseline_median / current_median
        improvement = (baseline_median - current_median) / baseline_median * 100
        print(f"  {name}")
        print(f"    exact output; {baseline_median:.3f}s -> {current_median:.3f}s")
        print(f"    {speedup:.2f}x ({improvement:.1f}% faster)")

    baseline_total = baseline["summary"]["median_total_seconds"]
    current_total = current["summary"]["median_total_seconds"]
    speedup = baseline_total / current_total
    improvement = (baseline_total - current_total) / baseline_total * 100
    print(f"  Aggregate median: {baseline_total:.3f}s -> {current_total:.3f}s")
    print(f"  Aggregate speedup: {speedup:.2f}x ({improvement:.1f}% faster)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="JSON file to receive benchmark results")
    parser.add_argument(
        "--input",
        action="append",
        dest="inputs",
        type=Path,
        help="document to benchmark; repeat to override the default matrix",
    )
    parser.add_argument("--warmup-input", type=Path, default=DEFAULT_WARMUP_INPUT)
    parser.add_argument(
        "--iterations", type=int, default=int(os.environ.get("NUM_ITERATIONS", "3"))
    )
    parser.add_argument("--compare", type=Path, help="baseline JSON to check and compare against")
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")
    args.inputs = args.inputs or list(DEFAULT_INPUTS)
    for path_arg in (*args.inputs, args.warmup_input):
        if not path_arg.is_file():
            parser.error(f"input file does not exist: {path_arg}")
    return args


def main() -> None:
    args = parse_args()
    results = run_benchmark(
        [input_path.resolve() for input_path in args.inputs],
        args.warmup_input.resolve(),
        args.iterations,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")

    for name, document in results["documents"].items():
        print(f"{name}: {document['seconds']['median']:.3f}s median")
        print(f"  {document['output']['element_count']} elements")
    print(f"Aggregate median: {results['summary']['median_total_seconds']:.3f}s")
    print(f"Results: {args.output}")
    if args.compare:
        compare_results(results, args.compare)


if __name__ == "__main__":
    main()
