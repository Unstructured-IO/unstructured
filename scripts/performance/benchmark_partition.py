#!/usr/bin/env python3
"""Measure partition() runtime over a fixed set of representative example-docs files.

Follows the same conventions as the existing scripts/performance tooling:
    - PDFs and images are run with strategy="hi_res".
    - Everything else is run with strategy="fast".
    - Each file is timed over NUM_ITERATIONS runs (after a warmup) and the
      average is recorded, matching time_partition.py behaviour.

Output is a JSON file mapping each file path to its average elapsed seconds,
plus a ``"__total__"`` key that is the sum of all per-file averages.

Results are saved to scripts/performance/partition-speed-test/ by default.

Usage:
    uv run --no-sync python scripts/performance/benchmark_partition.py [output.json]

    output.json  where results are written
                 (default: scripts/performance/partition-speed-test/benchmark_results.json)

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

# Configure logging
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
    # Other document types - fast
    ("example-docs/contains-pictures.docx", "fast"),
    ("example-docs/example-10k-1p.html", "fast"),
    ("example-docs/science-exploration-1p.pptx", "fast"),
]

NUM_ITERATIONS: int = int(os.environ.get("NUM_ITERATIONS", "1"))

RESULTS_DIR = Path(__file__).parent / "partition-speed-test"


def _warmup(filepath: str) -> None:
    """Run a single fast-strategy partition to warm the process up.

    Mirrors the warm_up_process() call in time_partition.py: if a warmup
    variant of the file exists under warmup-docs/ use that, otherwise fall
    back to the file itself.
    """
    from unstructured.partition.auto import partition

    warmup_dir = Path(__file__).parent / "warmup-docs"
    ext = Path(filepath).suffix
    warmup_file = warmup_dir / f"warmup{ext}"

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


def run_benchmark(repo_root: Path, output_path: Path | None = None) -> dict[str, float]:
    """Benchmark each file and return ``{rel_path: avg_seconds, "__total__": total}``.

    Args:
        repo_root:   Absolute path to the repository root.
        output_path: If given, results are written as JSON to this path.
    """
    results: dict[str, float] = {}
    missing: list[str] = []

    for rel_path, strategy in BENCHMARK_FILES:
        filepath = repo_root / rel_path
        if not filepath.exists():
            logger.warning(f"  WARNING: {rel_path} not found - skipping.")
            missing.append(rel_path)
            continue

        logger.info(f"  {rel_path}  (strategy={strategy}, iterations={NUM_ITERATIONS})")

        _warmup(str(filepath))
        avg = round(_measure(str(filepath), strategy, NUM_ITERATIONS), 3)
        results[rel_path] = avg
        logger.info(f"    avg {avg:.2f}s")

    total = round(sum(v for v in results.values()), 3)
    results["__total__"] = total

    logger.info(f"\nTotal (sum of averages) across {len(results) - 1} file(s): {total:.2f}s")
    if missing:
        logger.warning(f"Skipped {len(missing)} missing file(s): {', '.join(missing)}")

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2))
        logger.info(f"Results written to {output_path}")

    return results


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS_DIR / "benchmark_results.json"
    repo_root = Path(__file__).resolve().parent.parent.parent  # scripts/performance/ -> repo root

    logger.info("=" * 60)
    logger.info(f"Partition benchmark  (NUM_ITERATIONS={NUM_ITERATIONS})")
    logger.info("=" * 60)
    run_benchmark(repo_root, output_path)


if __name__ == "__main__":
    main()
