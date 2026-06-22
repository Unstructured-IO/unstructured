#!/usr/bin/env python3
"""Compare this run's partition() benchmark against a rolling baseline.

Why a rolling baseline (and not a single stored "best"):
    GitHub's shared ``ubuntu-latest`` runners vary in speed by ~1.6x run-to-run,
    and that variance scales the whole benchmark (partition work *and* fixed
    overhead). A single all-time-minimum baseline is therefore unbeatable the
    moment one lucky-fast runner records it -- every later run on a normal runner
    exceeds best*(1+threshold) and the check fails for everyone. (That is exactly
    what happened: a frozen 81s "best" vs a real ~130s fleet.)

    Instead we keep the last ``--window`` runs from ``main`` and compare against
    their **median**, which a single fast/slow outlier can't poison. The baseline
    tracks reality over time rather than ratcheting to an unrepeatable minimum.

Storage:
    Each ``main`` run is one immutable JSON record under ``HISTORY_DIR`` (synced
    to/from S3 by the workflow). This script never talks to S3 -- it only reads
    the local history dir and, with ``--record``, writes this run's record there
    for the workflow to upload. Pruning of old objects is an S3 lifecycle rule.

Usage:
    uv run --no-sync python scripts/performance/compare_benchmark.py \
        benchmark_results.json \
        HISTORY_DIR \
        [--threshold 0.30] [--window 20] [--min-samples 5] [--record]

    benchmark_results.json  this run's results from benchmark_partition.py
    HISTORY_DIR             dir of per-run history records (may be empty/missing)
    --threshold            regression allowance over the median (default 0.30)
    --window               number of most-recent records to median over (default 20)
    --min-samples          below this many records, warm-up (record + pass, no gate)
    --record               write this run's record into HISTORY_DIR (main runs only);
                           recording happens regardless of pass/fail so the baseline
                           can't get stuck.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import math
import os
import statistics
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _github_output(key: str, value: str) -> None:
    """Write a key=value pair to $GITHUB_OUTPUT when running in Actions."""
    gho = os.environ.get("GITHUB_OUTPUT")
    if gho:
        with open(gho, "a") as fh:
            fh.write(f"{key}={value}\n")


def _fmt(seconds: float) -> str:
    if seconds is None or math.isnan(seconds):
        return "    n/a"
    return f"{seconds:7.2f}s"


def _pct_diff(current: float, baseline: float) -> str:
    if not baseline:
        return "   n/a"
    diff = (current - baseline) / baseline * 100
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.1f}%"


def _runner_info() -> dict:
    """Best-effort CPU/nproc capture, purely for later visibility of variance."""
    cpu_model = None
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {"cpu_model": cpu_model, "nproc": os.cpu_count()}


def load_history(history_dir: Path) -> list[dict]:
    """Load every per-run record from HISTORY_DIR, sorted oldest -> newest."""
    if not history_dir.is_dir():
        return []
    records: list[dict] = []
    for f in history_dir.glob("*.json"):
        try:
            rec = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"skipping unreadable history record {f.name}: {e}")
            continue
        if "total" in rec:
            records.append(rec)
    records.sort(key=lambda r: r.get("timestamp") or "")
    return records


def build_record(current: dict) -> dict:
    """Build this run's history record from results + CI environment metadata."""
    now = dt.datetime.now(dt.timezone.utc)
    sha = os.environ.get("GITHUB_SHA", "")
    return {
        "sha": sha,
        "run_id": int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else None,
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": os.environ.get("GITHUB_EVENT_NAME"),
        "ref": os.environ.get("GITHUB_REF_NAME"),
        "seed": False,
        "iterations": int(os.environ.get("NUM_ITERATIONS", "0")) or None,
        "runner": _runner_info(),
        "total": round(current["__total__"], 2),
        "per_file": {k: round(v, 4) for k, v in current.items() if k != "__total__"},
    }


def write_record(history_dir: Path, record: dict) -> Path:
    """Write the record into HISTORY_DIR, replacing any prior record for this sha."""
    history_dir.mkdir(parents=True, exist_ok=True)
    sha = record.get("sha") or ""
    # Dedupe: a re-run of the same commit supersedes its earlier record.
    if sha:
        for f in history_dir.glob("*.json"):
            try:
                if json.loads(f.read_text()).get("sha") == sha:
                    f.unlink()
            except (json.JSONDecodeError, OSError):
                continue
    ts_compact = record["timestamp"].replace("-", "").replace(":", "")
    out = history_dir / f"{ts_compact}-{sha[:12]}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    return out


def _median_per_file(window: list[dict]) -> dict[str, float]:
    files: set[str] = set()
    for r in window:
        files.update(r.get("per_file", {}).keys())
    medians: dict[str, float] = {}
    for fname in files:
        vals = [r["per_file"][fname] for r in window if fname in r.get("per_file", {})]
        if vals:
            medians[fname] = statistics.median(vals)
    return medians


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("current_results", type=Path)
    ap.add_argument("history_dir", type=Path)
    ap.add_argument("--threshold", type=float, default=0.30)
    ap.add_argument("--window", type=int, default=20)
    ap.add_argument("--min-samples", type=int, default=5)
    ap.add_argument(
        "--record", action="store_true", help="write this run into the history (main runs)"
    )
    args = ap.parse_args()

    current: dict[str, float] = json.loads(args.current_results.read_text())
    current_total: float = current["__total__"]

    history = load_history(args.history_dir)
    window = history[-args.window :]

    # Record first (main runs only) so the baseline always reflects reality,
    # regardless of whether this run passes the gate -- the opposite of the old
    # min-ratchet, which could only ever lower the bar and so got stuck.
    if args.record:
        rec_path = write_record(args.history_dir, build_record(current))
        logger.info(f"recorded this run -> {rec_path.name}")

    # Warm-up: not enough history to gate yet. Observe and pass.
    if len(window) < args.min_samples:
        logger.info(
            f"WARM-UP: {len(window)} of {args.min_samples} baseline samples present "
            f"-- recording only, not gating. (current total {current_total:.2f}s)"
        )
        _github_output("regression", "false")
        _github_output("warmup", "true")
        sys.exit(0)

    baseline = statistics.median(r["total"] for r in window)
    limit = baseline * (1.0 + args.threshold)
    per_file_baseline = _median_per_file(window)

    all_files = sorted((set(current) | set(per_file_baseline)) - {"__total__"})
    col_w = max((len(f) for f in all_files), default=40) + 2
    header = f"{'File':<{col_w}} {'Current':>9}  {'Median':>9}  {'Delta':>8}"
    logger.info("=" * len(header))
    logger.info(f"Partition benchmark vs rolling median of last {len(window)} main runs")
    logger.info("=" * len(header))
    logger.info(header)
    logger.info("-" * len(header))
    for fname in all_files:
        c = current.get(fname, float("nan"))
        b = per_file_baseline.get(fname, float("nan"))
        logger.info(f"{fname:<{col_w}} {_fmt(c)}  {_fmt(b)}  {_pct_diff(c, b):>8}")
    logger.info("-" * len(header))
    logger.info(
        f"{'TOTAL':<{col_w}} {_fmt(current_total)}  {_fmt(baseline)}"
        f"  {_pct_diff(current_total, baseline):>8}"
    )
    logger.info("")
    logger.info(
        f"Baseline : median of {len(window)} runs = {baseline:.2f}s  "
        f"(threshold {args.threshold * 100:.0f}%, fail if > {limit:.2f}s)"
    )
    logger.info("")

    if current_total > limit:
        excess_pct = (current_total - baseline) / baseline * 100
        logger.error(
            f"FAIL: current runtime {current_total:.2f}s exceeds the median baseline "
            f"{baseline:.2f}s by {excess_pct:.1f}% (threshold {args.threshold * 100:.0f}%, "
            f"limit {limit:.2f}s)."
        )
        _github_output("regression", "true")
        sys.exit(1)

    logger.info(
        f"PASS: {current_total:.2f}s is within {args.threshold * 100:.0f}% of the "
        f"median baseline {baseline:.2f}s."
    )
    _github_output("regression", "false")
    sys.exit(0)


if __name__ == "__main__":
    main()
