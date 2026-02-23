#!/usr/bin/env python3
"""Measure partition() runtime over a fixed set of representative example-docs files.

Follows the same conventions as the existing scripts/performance tooling:
    - PDFs are run with strategy="hi_res".
    - Everything else is run with strategy="fast".
    - Each file is timed over NUM_ITERATIONS runs (after a warmup) and the
      average is recorded, matching time_partition.py behaviour.

Writes the total elapsed seconds (integer) to $GITHUB_OUTPUT as::

    duration=<seconds>

so the calling workflow step can reference it as::

    ${{ steps.<step_id>.outputs.duration }}

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

# ---------------------------------------------------------------------------
# File list (relative to repo root).
# Each entry is (path, strategy).
# hi_res  - PDFs and images (exercises the full OCR / layout-detection stack)
# fast    - all other document types (exercises text-extraction paths)
# Mirrors the HI_RES_STRATEGY_FILES pattern in benchmark-local.sh.
# ---------------------------------------------------------------------------
BENCHMARK_FILES: list[tuple[str, str]] = [
    # PDFs - hi_res
    ("example-docs/pdf/a1977-backus-p21.pdf", "hi_res"),
    ("example-docs/pdf/copy-protected.pdf", "hi_res"),
    ("example-docs/pdf/reliance.pdf", "hi_res"),
    ("example-docs/pdf/pdf-with-ocr-text.pdf", "hi_res"),
    ("example-docs/pdf/layout-parser-paper.pdf", "hi_res"),
    ("example-docs/pdf/layout-parser-paper-with-table.pdf", "hi_res"),
    ("example-docs/pdf/failure-after-repair.pdf", "hi_res"),
    # Other document types - fast
    ("example-docs/contains-pictures.docx", "fast"),
    ("example-docs/example-10k-1p.html", "fast"),
    ("example-docs/science-exploration-1p.pptx", "fast"),
]

NUM_ITERATIONS: int = int(os.environ.get("NUM_ITERATIONS", "1"))


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
    repo_root = Path(__file__).resolve().parent.parent.parent  # scripts/performance/ -> repo root

    logger.info("=" * 60)
    logger.info(f"Partition benchmark  (NUM_ITERATIONS={NUM_ITERATIONS})")
    logger.info("=" * 60)

    grand_start = time.perf_counter()

    for rel_path, strategy in BENCHMARK_FILES:
        filepath = repo_root / rel_path
        if not filepath.exists():
            logger.warning(f"  WARNING: {rel_path} not found - skipping.")
            continue

        logger.info(f"  {rel_path}  (strategy={strategy}, iterations={NUM_ITERATIONS})")
        _warmup(str(filepath))
        avg = _measure(str(filepath), strategy, NUM_ITERATIONS)
        logger.info(f"    avg {avg:.2f}s")

    total_seconds = int(time.perf_counter() - grand_start)
    logger.info(f"\nTotal wall-clock time: {total_seconds}s")

    _set_github_output("duration", str(total_seconds))


if __name__ == "__main__":
    main()
