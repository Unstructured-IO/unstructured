#!/usr/bin/env python3
"""Measure partition() runtime over a fixed set of representative example-docs files.

Follows the same conventions as the existing scripts/performance tooling:
    - PDFs are run with strategy="hi_res".
    - Everything else is run with strategy="fast".
    - Each file is timed over NUM_ITERATIONS runs (after a warmup) and the
      average is recorded, matching time_partition.py behaviour.

Writes the total elapsed seconds to:
    scripts/performance/partition-speed-test/current-runtime.txt

The calling workflow step reads that file and sets $GITHUB_OUTPUT explicitly.

Usage:
    uv run --no-sync python scripts/performance/benchmark_partition.py

Environment variables:
    NUM_ITERATIONS   number of timed iterations per file (default: 1)
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

BENCHMARK_FILES: list[tuple[str, str]] = [
    # PDFs - hi_res
    ("example-docs/pdf/a1977-backus-p21.pdf", "hi_res"),
    ("example-docs/pdf/copy-protected.pdf", "hi_res"),
    # Other document types - fast
    ("example-docs/contains-pictures.docx", "fast"),
    ("example-docs/example-10k-1p.html", "fast"),
    ("example-docs/science-exploration-1p.pptx", "fast"),
]

NUM_ITERATIONS: int = int(os.environ.get("NUM_ITERATIONS", "1"))

RESULTS_DIR = Path(__file__).parent / "partition-speed-test"
CURRENT_RUNTIME_FILE = RESULTS_DIR / "current-runtime.txt"


def _warmup(filepath: str) -> None:
    """Run a single fast-strategy partition to warm the process up.

    Mirrors warm_up_process() in time_partition.py: uses a warmup-docs/
    variant if present, otherwise falls back to the file itself.
    """
    from unstructured.partition.auto import partition

    warmup_dir = Path(__file__).parent / "warmup-docs"
    warmup_file = warmup_dir / f"warmup{Path(filepath).suffix}"
    target = str(warmup_file) if warmup_file.exists() else filepath
    partition(target, strategy="fast")


def _measure(filepath: str, strategy: str, iterations: int) -> float:
    """Return the average wall-clock seconds for partitioning *filepath*.

    Identical logic to time_partition.measure_execution_time().
    """
    from unstructured.partition.auto import partition

    total = 0.0
    for _ in range(iterations):
        t0 = time.time()
        partition(filepath, strategy=strategy)
        total += time.time() - t0
    return total / iterations


def main() -> None:
    repo_root = (
        Path(__file__).resolve().parent.parent.parent
    )  # scripts/performance/ -> repo root

    logger.info("=" * 60)
    logger.info(f"Partition benchmark  (NUM_ITERATIONS={NUM_ITERATIONS})")
    logger.info("=" * 60)

    grand_start = time.time()

    for rel_path, strategy in BENCHMARK_FILES:
        filepath = repo_root / rel_path
        if not filepath.exists():
            logger.warning(f"  WARNING: {rel_path} not found - skipping.")
            continue

        logger.info(f"  {rel_path}  (strategy={strategy}, iterations={NUM_ITERATIONS})")
        _warmup(str(filepath))
        avg = _measure(str(filepath), strategy, NUM_ITERATIONS)
        logger.info(f"    avg {avg:.2f}s")

    total_seconds = int(time.time() - grand_start)
    logger.info(f"\nTotal wall-clock time: {total_seconds}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_RUNTIME_FILE.write_text(str(total_seconds))
    logger.info(f"Duration written to {CURRENT_RUNTIME_FILE}")


if __name__ == "__main__":
    main()
