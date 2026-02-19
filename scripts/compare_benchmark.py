#!/usr/bin/env python3
"""Compare current benchmark results against the stored best runtime.

The script:
  1. Loads the current benchmark results and the stored best (if any).
  2. Prints a per-file and total summary table.
  3. Exits 1 (fail) if the current ``__total__`` exceeds the best ``__total__``
     by more than the given threshold fraction.
  4. Updates the best-results file in-place when the current run is faster.
  5. Writes ``new_best`` and ``regression`` to ``$GITHUB_OUTPUT`` when set.

Values in both JSON files are average elapsed seconds per file, as written by
benchmark_partition.py (which follows the same averaging approach as
time_partition.py).

Usage:
    uv run --no-sync python scripts/performance/compare_benchmark.py \\
        current.json best.json [threshold]

    current.json  JSON produced by benchmark_partition.py for this run
    best.json     JSON produced by a previous run (the stored best); may not
                  exist yet on the very first run
    threshold     Regression allowance as a fraction, e.g. 0.20 for 20%
                  (default: 0.20)
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _github_output(key: str, value: str) -> None:
    """Write key=value to $GITHUB_OUTPUT when running inside GitHub Actions."""
    gho = os.environ.get("GITHUB_OUTPUT")
    if gho:
        with open(gho, "a") as fh:
            fh.write(f"{key}={value}\n")


def _fmt(seconds: float) -> str:
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
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)

    current_path = Path(sys.argv[1])
    best_path = Path(sys.argv[2])
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.20

    current: dict[str, float] = json.loads(current_path.read_text())
    current_total: float = current["__total__"]

    # ------------------------------------------------------------------
    # First-ever run – no stored best yet; save and exit cleanly.
    # ------------------------------------------------------------------
    if not best_path.exists():
        print("No stored best found – saving current run as the baseline.")
        print(f"  Total (sum of averages): {current_total:.2f}s")
        best_path.write_text(current_path.read_text())
        _github_output("new_best", "true")
        _github_output("regression", "false")
        sys.exit(0)

    best: dict[str, float] = json.loads(best_path.read_text())
    best_total: float = best["__total__"]
    limit: float = best_total * (1.0 + threshold)

    # Collect all file keys, excluding the __total__ sentinel
    all_files = sorted((set(current.keys()) | set(best.keys())) - {"__total__"})

    col_w = max((len(f) for f in all_files), default=40) + 2
    header = f"{'File':<{col_w}} {'Current (avg)':>13}  {'Best (avg)':>10}  {'Δ':>8}"
    sep = "=" * len(header)
    print(sep)
    print("Partition benchmark comparison")
    print(sep)
    print(header)
    print("-" * len(header))

    for fname in all_files:
        c = current.get(fname, float("nan"))
        b = best.get(fname, float("nan"))
        print(f"{fname:<{col_w}} {_fmt(c)}  {_fmt(b)}  {_pct_diff(c, b):>8}")

    print("-" * len(header))
    print(
        f"{'TOTAL':<{col_w}} {_fmt(current_total)}  {_fmt(best_total)}"
        f"  {_pct_diff(current_total, best_total):>8}"
    )
    print()
    print(f"Threshold : {threshold * 100:.0f}%  (fail if current > {limit:.2f}s)")
    print()

    # ------------------------------------------------------------------
    # Regression check
    # ------------------------------------------------------------------
    if current_total > limit:
        excess_pct = (current_total - best_total) / best_total * 100
        print(
            f"FAIL: current total {current_total:.2f}s exceeds best "
            f"{best_total:.2f}s by {excess_pct:.1f}% "
            f"(threshold {threshold * 100:.0f}%, limit {limit:.2f}s).",
            file=sys.stderr,
        )
        _github_output("new_best", "false")
        _github_output("regression", "true")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Pass – update stored best if the current run is faster
    # ------------------------------------------------------------------
    if current_total < best_total:
        improvement_pct = (best_total - current_total) / best_total * 100
        print(
            f"PASS (new best): {current_total:.2f}s is {improvement_pct:.1f}% faster than "
            f"previous best {best_total:.2f}s – updating stored best."
        )
        best_path.write_text(current_path.read_text())
        _github_output("new_best", "true")
    else:
        slack_pct = (current_total - best_total) / best_total * 100
        print(
            f"PASS: {current_total:.2f}s is {slack_pct:.1f}% slower than best "
            f"{best_total:.2f}s (within {threshold * 100:.0f}% threshold)."
        )
        _github_output("new_best", "false")

    _github_output("regression", "false")
    sys.exit(0)


if __name__ == "__main__":
    main()
