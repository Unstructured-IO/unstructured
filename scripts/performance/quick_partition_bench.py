"""Quick local benchmark for PDF partition cold/warm timing.

Examples:
  uv run --active --frozen --no-sync scripts/performance/quick_partition_bench.py \
    --pdf example-docs/pdf/DA-1p.pdf --strategy fast --repeats 4 --warmups 1 --mode both

  uv run --active --frozen --no-sync scripts/performance/quick_partition_bench.py \
    --pdf example-docs/pdf/DA-1p.pdf --pdf example-docs/pdf/chevron-page.pdf \
    --strategy hi_res --repeats 3 --warmups 1 --mode both
"""

import argparse
import io
import json
import statistics
import subprocess
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _partition_once(pdf: str, strategy: str) -> dict[str, object]:
    sink_out = io.StringIO()
    sink_err = io.StringIO()
    start = time.perf_counter()
    try:
        from unstructured.partition.auto import partition

        with redirect_stdout(sink_out), redirect_stderr(sink_err):
            elements = partition(filename=pdf, strategy=strategy)
        return {
            "ok": True,
            "elapsed_s": time.perf_counter() - start,
            "elements": len(elements),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "mean_s": statistics.mean(values),
        "median_s": statistics.median(values),
        "min_s": min(values),
        "max_s": max(values),
        "stdev_s": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def _run_cold(pdf: str, strategy: str, repeats: int) -> tuple[list[float], int, list[str]]:
    times: list[float] = []
    elements = -1
    errors: list[str] = []

    for _ in range(repeats):
        proc = subprocess.run(
            [
                sys.executable,
                __file__,
                "--_child",
                "--pdf",
                pdf,
                "--strategy",
                strategy,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
        json_line = next((line for line in reversed(lines) if line.startswith("{")), "")
        if not json_line:
            stderr_tail = (proc.stderr or "").strip().splitlines()
            detail = stderr_tail[-1] if stderr_tail else "no json output"
            errors.append(f"child failed rc={proc.returncode} ({detail})")
            continue

        row = json.loads(json_line)
        if bool(row.get("ok")):
            times.append(float(row["elapsed_s"]))
            elements = int(row["elements"])
        else:
            errors.append(str(row.get("error", "unknown error")))

    return times, elements, errors


def _run_warm(
    pdf: str,
    strategy: str,
    repeats: int,
    warmups: int,
) -> tuple[list[float], int, list[str]]:
    errors: list[str] = []

    for _ in range(warmups):
        row = _partition_once(pdf=pdf, strategy=strategy)
        if not bool(row.get("ok")):
            errors.append(str(row.get("error", "unknown error")))
            return [], -1, errors

    times: list[float] = []
    elements = -1
    for _ in range(repeats):
        row = _partition_once(pdf=pdf, strategy=strategy)
        if bool(row.get("ok")):
            times.append(float(row["elapsed_s"]))
            elements = int(row["elements"])
        else:
            errors.append(str(row.get("error", "unknown error")))

    return times, elements, errors


def _collect_pdfs(pdf_args: list[str], pdf_dir_args: list[str]) -> list[str]:
    paths = [str(Path(p)) for p in pdf_args]

    for pdf_dir in pdf_dir_args:
        root = Path(pdf_dir)
        if not root.is_dir():
            raise FileNotFoundError(f"pdf-dir does not exist: {root}")
        paths.extend(str(p) for p in sorted(root.rglob("*.pdf")))

    if not paths:
        raise ValueError("Provide at least one --pdf or --pdf-dir")

    deduped = [Path(p) for p in dict.fromkeys(paths)]
    missing = [str(p) for p in deduped if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing files: {', '.join(missing)}")

    return [str(p) for p in deduped]


def _print_mode(label: str, values: list[float], elements: int, errors: list[str]) -> None:
    if not values:
        first = errors[0] if errors else "unknown error"
        print(f"  {label} FAILED ({first})", flush=True)
        return

    s = _summary(values)
    print(
        f"  {label} mean={s['mean_s']:.4f}s median={s['median_s']:.4f}s "
        f"min={s['min_s']:.4f}s max={s['max_s']:.4f}s n={len(values)} elements={elements}",
        flush=True,
    )
    if errors:
        print(f"  {label} partial_failures={len(errors)} first_error={errors[0]}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick local PDF partition benchmark")
    parser.add_argument("--pdf", action="append", default=[], help="PDF path (repeatable)")
    parser.add_argument("--pdf-dir", action="append", default=[], help="Directory of PDFs")
    parser.add_argument("--strategy", default="fast", choices=["fast", "hi_res", "auto"])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--mode", default="both", choices=["cold", "warm", "both"])
    parser.add_argument("--json-out", default="", help="Optional JSON output path")
    parser.add_argument("--_child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args._child:
        print(json.dumps(_partition_once(args.pdf[0], args.strategy)), flush=True)
        return

    pdfs = _collect_pdfs(args.pdf, args.pdf_dir)

    print(
        f"strategy={args.strategy} mode={args.mode} repeats={args.repeats} "
        f"warmups={args.warmups} pdf_count={len(pdfs)}",
        flush=True,
    )

    by_mode_times: dict[str, list[float]] = {"cold": [], "warm": []}
    by_mode_file_means: dict[str, list[float]] = {"cold": [], "warm": []}
    by_mode_failed_files: dict[str, int] = {"cold": 0, "warm": 0}
    results: list[dict[str, object]] = []

    for pdf in pdfs:
        row: dict[str, object] = {"pdf": pdf}
        print(f"FILE {pdf}", flush=True)

        if args.mode in ("cold", "both"):
            times, elements, errors = _run_cold(pdf, args.strategy, args.repeats)
            _print_mode("cold", times, elements, errors)
            if times:
                by_mode_times["cold"].extend(times)
                by_mode_file_means["cold"].append(statistics.mean(times))
                row["cold"] = {"ok": True, "times_s": times, "elements": elements, "errors": errors}
            else:
                by_mode_failed_files["cold"] += 1
                row["cold"] = {"ok": False, "errors": errors}

        if args.mode in ("warm", "both"):
            times, elements, errors = _run_warm(pdf, args.strategy, args.repeats, args.warmups)
            _print_mode("warm", times, elements, errors)
            if times:
                by_mode_times["warm"].extend(times)
                by_mode_file_means["warm"].append(statistics.mean(times))
                row["warm"] = {
                    "ok": True,
                    "times_s": times,
                    "elements": elements,
                    "errors": errors,
                    "warmups": args.warmups,
                }
            else:
                by_mode_failed_files["warm"] += 1
                row["warm"] = {"ok": False, "errors": errors, "warmups": args.warmups}

        results.append(row)

    aggregate: dict[str, object] = {}
    print("AGGREGATE", flush=True)
    for mode in ("cold", "warm"):
        times = by_mode_times[mode]
        if not times:
            continue
        s = _summary(times)
        file_mean = statistics.mean(by_mode_file_means[mode])
        succeeded = len(by_mode_file_means[mode])
        failed = by_mode_failed_files[mode]
        aggregate[mode] = {
            "summary": s,
            "file_mean_s": file_mean,
            "samples": len(times),
            "succeeded_files": succeeded,
            "failed_files": failed,
        }
        print(
            f"  {mode} succeeded_files={succeeded} failed_files={failed} "
            f"file_mean={file_mean:.4f}s mean={s['mean_s']:.4f}s median={s['median_s']:.4f}s "
            f"min={s['min_s']:.4f}s max={s['max_s']:.4f}s stdev={s['stdev_s']:.4f}s samples={len(times)}",
            flush=True,
        )

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "strategy": args.strategy,
                    "mode": args.mode,
                    "repeats": args.repeats,
                    "warmups": args.warmups,
                    "pdf_count": len(pdfs),
                    "per_file": results,
                    "aggregate": aggregate,
                },
                indent=2,
            )
        )
        print(f"json_out={out}", flush=True)


if __name__ == "__main__":
    main()
