#!/usr/bin/env python3
"""Measure partition() runtime over a fixed set of representative example-docs files.

Follows the same conventions as the existing scripts/performance tooling:
    - PDFs and images are run with strategy="hi_res".
    - Everything else is run with strategy="fast".
    - Each file is timed over NUM_ITERATIONS runs (after a warmup) and the
      average is recorded, matching time_partition.py behaviour.

Writes a JSON file mapping each file to its average runtime, plus a ``__total__``
key with the wall-clock total.  An optional positional argument sets the output
path (default: scripts/performance/partition-speed-test/benchmark_results.json).

Also writes the total duration to $GITHUB_OUTPUT as ``duration=<seconds>``.

Usage:
    uv run --no-sync python scripts/performance/benchmark_partition.py [output.json]

Environment variables:
    NUM_ITERATIONS   number of timed iterations per file (default: 1)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

from unstructured.partition.auto import partition

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


BENCHMARK_FILES: list[tuple[str, str]] = [
    # PDFs - hi_res
    ("example-docs/pdf/a1977-backus-p21.pdf", "hi_res"),
    ("example-docs/pdf/copy-protected.pdf", "hi_res"),
    ("example-docs/pdf/reliance.pdf", "hi_res"),
    ("example-docs/pdf/pdf-with-ocr-text.pdf", "hi_res"),
    # Images - hi_res
    ("example-docs/double-column-A.jpg", "hi_res"),
    ("example-docs/double-column-B.jpg", "hi_res"),
    ("example-docs/embedded-images-tables.jpg", "hi_res"),
    # Other document types - fast
    ("example-docs/contains-pictures.docx", "fast"),
    ("example-docs/example-10k-1p.html", "fast"),
    ("example-docs/science-exploration-1p.pptx", "fast"),
]

NUM_ITERATIONS: int = int(os.environ.get("NUM_ITERATIONS", "1"))

DEFAULT_OUTPUT = Path(__file__).parent / "partition-speed-test" / "benchmark_results.json"


def _warmup(filepath: str) -> None:
    """Run a single fast-strategy partition to warm the process up.

    Mirrors warm_up_process() in time_partition.py: uses a warmup-docs/
    variant if present, otherwise falls back to the file itself.
    """

    warmup_dir = Path(__file__).parent / "warmup-docs"
    warmup_file = warmup_dir / f"warmup{Path(filepath).suffix}"
    target = str(warmup_file) if warmup_file.exists() else filepath
    partition(target, strategy="fast")


def _measure(filepath: str, strategy: str, iterations: int) -> float:
    """Return the average wall-clock seconds for partitioning *filepath*.

    Identical logic to time_partition.measure_execution_time().
    """

    total = 0.0
    for _ in range(iterations):
        t0 = time.perf_counter()
        partition(filepath, strategy=strategy)
        total += time.perf_counter() - t0
    return total / iterations


def _set_github_output(key: str, value: str) -> None:
    """Write key=value to $GITHUB_OUTPUT when running in Actions."""
    gho = os.environ.get("GITHUB_OUTPUT")
    if gho:
        with open(gho, "a") as fh:
            fh.write(f"{key}={value}\n")


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    repo_root = Path(__file__).resolve().parent.parent.parent  # scripts/performance/ -> repo root

    logger.info("=" * 60)
    logger.info(f"Partition benchmark  (NUM_ITERATIONS={NUM_ITERATIONS})")
    logger.info("=" * 60)

    results: dict[str, float] = {}
    grand_start = time.perf_counter()

    for rel_path, strategy in BENCHMARK_FILES:
        filepath = repo_root / rel_path
        if not filepath.exists():
            logger.warning(f"  WARNING: {rel_path} not found – skipping.")
            continue

        logger.info(f"  {rel_path}  (strategy={strategy}, iterations={NUM_ITERATIONS})")
        _warmup(str(filepath))
        avg = _measure(str(filepath), strategy, NUM_ITERATIONS)
        results[rel_path] = round(avg, 4)
        logger.info(f"    avg {avg:.2f}s")

    total_seconds = round(time.perf_counter() - grand_start, 2)
    results["__total__"] = total_seconds

    logger.info(f"\nTotal wall-clock time: {total_seconds}s")

    # Write JSON results file (consumed by compare_benchmark.py)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2) + "\n")
    logger.info(f"Results written to {output_path}")

    # Also expose total as a GitHub Actions step output
    _set_github_output("duration", str(int(total_seconds)))


if __name__ == "__main__":
    main()
