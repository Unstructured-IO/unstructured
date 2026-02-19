#!/usr/bin/env python3
"""Compare current benchmark results against the stored best runtime.

The script:
    1. Loads the current benchmark results and the stored best (if any).
    2. Logs a per-file and total summary table.
    3. Exits 1 (fail) if the current total exceeds the best total by more than
       the given threshold fraction.
    4. Updates the best-results file in-place when the current run is faster
       (establishes a new record).
    5. Writes GitHub Actions step outputs ``new_best`` and ``regression`` when
       the ``GITHUB_OUTPUT`` environment variable is set.

Usage:
    uv run --no-sync python scripts/performance/compare_benchmark.py \
        scripts/performance/partition-speed-test/benchmark_results.json \
        scripts/performance/partition-speed-test/benchmark_best.json \
        [threshold]

    current.json  JSON produced by benchmark_partition.py for this run
    best.json     JSON produced by a previous run (the stored best); may not
                  exist yet on the very first run
    threshold     Float regression allowance, e.g. 0.20 for 20% (default 0.20)
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _github_output(key: str, value: str) -> None:
    """Write a key=value pair to $GITHUB_OUTPUT when running in Actions."""
    gho = os.environ.get("GITHUB_OUTPUT")
    if gho:
        with open(gho, "a") as fh:
            fh.write(f"{key}={value}\n")


def _fmt(seconds: float) -> str:
    """Format a duration, handling NaN for files missing from one side."""
    if math.isnan(seconds):
        return "    n/a"
    return f"{seconds:7.2f}s"


def _pct_diff(current: float, best: float) -> str:
    if best == 0:
        return "   n/a"
    diff = (current - best) / best * 100
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.1f}%"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)

    current_path = Path(sys.argv[1])
    best_path = Path(sys.argv[2])
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.20

    # ------------------------------------------------------------------
    # Load current results
    # ------------------------------------------------------------------
    current: dict[str, float] = json.loads(current_path.read_text())
    current_total: float = current["__total__"]

    # ------------------------------------------------------------------
    # First-ever run - no stored best yet
    # ------------------------------------------------------------------
    if not best_path.exists():
        logger.info("No stored best found - saving current run as the baseline.")
        logger.info(f"  Total: {current_total:.2f}s")
        best_path.parent.mkdir(parents=True, exist_ok=True)
        best_path.write_text(current_path.read_text())
        _github_output("new_best", "true")
        _github_output("regression", "false")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Normal comparison
    # ------------------------------------------------------------------
    best: dict[str, float] = json.loads(best_path.read_text())
    best_total: float = best["__total__"]
    limit: float = best_total * (1.0 + threshold)

    # Collect all file keys (exclude the __total__ sentinel)
    all_files = sorted((set(current.keys()) | set(best.keys())) - {"__total__"})

    col_w = max((len(f) for f in all_files), default=40) + 2
    header = f"{'File':<{col_w}} {'Current':>9}  {'Best':>9}  {'Delta':>8}"
    logger.info("=" * len(header))
    logger.info("Partition benchmark comparison")
    logger.info("=" * len(header))
    logger.info(header)
    logger.info("-" * len(header))

    for fname in all_files:
        c = current.get(fname, float("nan"))
        b = best.get(fname, float("nan"))
        logger.info(f"{fname:<{col_w}} {_fmt(c)}  {_fmt(b)}  {_pct_diff(c, b):>8}")

    logger.info("-" * len(header))
    logger.info(
        f"{'TOTAL':<{col_w}} {_fmt(current_total)}  {_fmt(best_total)}"
        f"  {_pct_diff(current_total, best_total):>8}"
    )
    logger.info("")
    logger.info(f"Threshold : {threshold * 100:.0f}%  (fail if current > {limit:.2f}s)")
    logger.info("")

    # ------------------------------------------------------------------
    # Fail on regression
    # ------------------------------------------------------------------
    if current_total > limit:
        excess_pct = (current_total - best_total) / best_total * 100
        logger.error(
            f"FAIL: current runtime {current_total:.2f}s exceeds best "
            f"{best_total:.2f}s by {excess_pct:.1f}% "
            f"(threshold {threshold * 100:.0f}%, limit {limit:.2f}s)."
        )
        _github_output("new_best", "false")
        _github_output("regression", "true")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Pass - record new best if current is faster
    # ------------------------------------------------------------------
    if current_total < best_total:
        improvement_pct = (best_total - current_total) / best_total * 100
        logger.info(
            f"PASS (new best): {current_total:.2f}s is {improvement_pct:.1f}% "
            f"faster than the previous best {best_total:.2f}s - updating stored best."
        )
        best_path.write_text(current_path.read_text())
        _github_output("new_best", "true")
    else:
        slack_pct = (current_total - best_total) / best_total * 100
        logger.info(
            f"PASS: {current_total:.2f}s is {slack_pct:.1f}% slower than best "
            f"{best_total:.2f}s (within {threshold * 100:.0f}% threshold)."
        )
        _github_output("new_best", "false")

    _github_output("regression", "false")
    sys.exit(0)


if __name__ == "__main__":
    main()
