"""Benchmark XLSX connected-component detection on generated worksheets.

This local utility compares the current sparse implementation against a dense
NetworkX grid-graph reference that mirrors the previous implementation.

Run from the repository root:

    uv run --extra xlsx --with networkx python \
        scripts/performance/benchmark_xlsx_connected_components.py

Use ``--case`` to run one generated shape, or ``--work-dir`` to keep the generated
XLSX files for inspection.
"""

from __future__ import annotations

import argparse
import gc
import json
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import psutil

from unstructured.partition.xlsx import _ConnectedComponent, _ConnectedComponents


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    rows: int
    cols: int
    builder: Callable[[int, int], pd.DataFrame]


@dataclass(frozen=True)
class Measurement:
    seconds: float
    baseline_rss_mb: float
    peak_rss_mb: float
    peak_delta_mb: float
    component_count: int

    @classmethod
    def from_json(cls, value: str) -> Measurement:
        measurement_dict = json.loads(value)
        return cls(
            seconds=measurement_dict["seconds"],
            baseline_rss_mb=measurement_dict["baseline_rss_mb"],
            peak_rss_mb=measurement_dict["peak_rss_mb"],
            peak_delta_mb=measurement_dict["peak_delta_mb"],
            component_count=measurement_dict["component_count"],
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "seconds": self.seconds,
                "baseline_rss_mb": self.baseline_rss_mb,
                "peak_rss_mb": self.peak_rss_mb,
                "peak_delta_mb": self.peak_delta_mb,
                "component_count": self.component_count,
            }
        )


def main() -> None:
    args = _parse_args()
    if args.worker:
        print(_measure_worker(args).to_json())
        return

    cases = [case for case in _cases() if args.case in (None, case.name)]
    if not cases:
        available_cases = ", ".join(case.name for case in _cases())
        raise SystemExit(f"Unknown case {args.case!r}. Available cases: {available_cases}")

    with _workspace(args.work_dir) as work_dir:
        print(f"Generated worksheet directory: {work_dir}")
        print(
            "case,algorithm,components,seconds,baseline_rss_mb,peak_rss_mb,peak_delta_mb"
        )

        for case in cases:
            worksheet_path = _write_worksheet(case, work_dir, args.storage)

            for algorithm_name in ("sparse", "dense"):
                measurement = _measure_in_subprocess(
                    algorithm_name, worksheet_path, args.storage, args.repeat
                )
                print(
                    f"{case.name},{algorithm_name},{measurement.component_count},"
                    f"{measurement.seconds:.4f},{measurement.baseline_rss_mb:.1f},"
                    f"{measurement.peak_rss_mb:.1f},{measurement.peak_delta_mb:.1f}"
                )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=[case.name for case in _cases()],
        help="Run only one generated worksheet shape.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="Number of times to repeat each connected-components measurement.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Directory for generated XLSX files. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--storage",
        choices=["xlsx", "pickle"],
        default="xlsx",
        help=(
            "How to pass generated worksheets to worker subprocesses. Use xlsx for end-to-end "
            "generated files, or pickle when XLSX writer dependencies are unavailable."
        ),
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--algorithm", choices=["sparse", "dense"], help=argparse.SUPPRESS)
    parser.add_argument("--input-path", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args()


@contextmanager
def _workspace(work_dir: Path | None) -> Iterator[Path]:
    if work_dir is not None:
        work_dir.mkdir(parents=True, exist_ok=True)
        yield work_dir
        return

    with tempfile.TemporaryDirectory(prefix="xlsx-components-") as tmp_dir:
        yield Path(tmp_dir)


def _cases() -> list[BenchmarkCase]:
    return [
        BenchmarkCase("dense_table", 800, 30, _dense_table),
        BenchmarkCase("sparse_wide_edges", 2500, 600, _sparse_wide_edges),
        BenchmarkCase("separated_blocks", 1800, 120, _separated_blocks),
    ]


def _write_worksheet(case: BenchmarkCase, work_dir: Path, storage: str) -> Path:
    worksheet_df = case.builder(case.rows, case.cols)
    if storage == "xlsx":
        xlsx_path = work_dir / f"{case.name}.xlsx"
        worksheet_df.to_excel(xlsx_path, index=False, header=False)
        return xlsx_path

    pickle_path = work_dir / f"{case.name}.pkl"
    worksheet_df.to_pickle(pickle_path)
    return pickle_path


def _dense_table(rows: int, cols: int) -> pd.DataFrame:
    return pd.DataFrame(
        [[f"r{row_idx}c{col_idx}" for col_idx in range(cols)] for row_idx in range(rows)]
    )


def _sparse_wide_edges(rows: int, cols: int) -> pd.DataFrame:
    worksheet = pd.DataFrame(None, index=range(rows), columns=range(cols), dtype=object)
    for row_idx in range(0, rows, 100):
        worksheet.iat[row_idx, 0] = f"left-{row_idx}"
        worksheet.iat[row_idx, cols - 1] = f"right-{row_idx}"

    worksheet.iat[rows - 2, cols - 2] = "footer"
    worksheet.iat[rows - 2, cols - 1] = "value"
    worksheet.iat[rows - 1, cols - 2] = "total"
    worksheet.iat[rows - 1, cols - 1] = 100
    return worksheet


def _separated_blocks(rows: int, cols: int) -> pd.DataFrame:
    worksheet = pd.DataFrame(None, index=range(rows), columns=range(cols), dtype=object)
    block_width = 8
    block_height = 12

    for block_idx, start_row in enumerate(range(0, rows - block_height, 80)):
        start_col = (block_idx * 17) % (cols - block_width)
        worksheet.iat[start_row, start_col] = f"Block {block_idx}"
        for row_offset in range(1, block_height):
            for col_offset in range(block_width):
                worksheet.iat[start_row + row_offset, start_col + col_offset] = (
                    f"{block_idx}-{row_offset}-{col_offset}"
                )

    return worksheet


def _measure_in_subprocess(
    algorithm_name: str, worksheet_path: Path, storage: str, repeat: int
) -> Measurement:
    measurements = []
    for _ in range(repeat):
        completed_process = subprocess.run(
            [
                sys.executable,
                __file__,
                "--worker",
                "--algorithm",
                algorithm_name,
                "--input-path",
                str(worksheet_path),
                "--storage",
                storage,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        measurements.append(Measurement.from_json(completed_process.stdout))

    return min(measurements, key=lambda measurement: measurement.seconds)


def _measure_worker(args: argparse.Namespace) -> Measurement:
    if args.algorithm is None or args.input_path is None:
        raise SystemExit("--worker requires --algorithm and --input-path")

    worksheet_df = _read_worksheet(args.input_path, args.storage)
    benchmark_function = (
        _sparse_connected_components
        if args.algorithm == "sparse"
        else _dense_connected_components
    )
    return _measure(lambda: benchmark_function(worksheet_df))


def _read_worksheet(input_path: Path, storage: str) -> pd.DataFrame:
    if storage == "xlsx":
        return pd.read_excel(input_path, header=None)

    return pd.read_pickle(input_path)


def _sparse_connected_components(worksheet_df: pd.DataFrame) -> list[_ConnectedComponent]:
    return list(_ConnectedComponents.from_worksheet_df(worksheet_df))


def _dense_connected_components(worksheet_df: pd.DataFrame) -> list[_ConnectedComponent]:
    max_row, max_col = worksheet_df.shape
    node_array = np.indices((max_row, max_col)).T
    empty_cells = worksheet_df.isna().T
    nodes_to_remove = [tuple(pair) for pair in node_array[empty_cells]]

    graph = nx.grid_2d_graph(max_row, max_col)
    graph.remove_nodes_from(nodes_to_remove)

    connected_components = [
        _ConnectedComponent(worksheet_df, component_node_set)
        for component_node_set in nx.connected_components(graph)
    ]
    return list(_ConnectedComponents(worksheet_df)._merge_overlapping_tables(connected_components))


def _measure(benchmark_function: Callable[[], list[_ConnectedComponent]]) -> Measurement:
    gc.collect()
    process = psutil.Process()
    baseline_rss = process.memory_info().rss
    peak_rss = baseline_rss
    stop_sampling = threading.Event()

    def sample_rss() -> None:
        nonlocal peak_rss
        while not stop_sampling.is_set():
            peak_rss = max(peak_rss, process.memory_info().rss)
            time.sleep(0.005)

    sampler = threading.Thread(target=sample_rss)
    sampler.start()
    start_time = time.perf_counter()
    components = benchmark_function()
    seconds = time.perf_counter() - start_time
    peak_rss = max(peak_rss, process.memory_info().rss)
    stop_sampling.set()
    sampler.join()

    return Measurement(
        seconds=seconds,
        baseline_rss_mb=baseline_rss / 1024 / 1024,
        peak_rss_mb=peak_rss / 1024 / 1024,
        peak_delta_mb=(peak_rss - baseline_rss) / 1024 / 1024,
        component_count=len(components),
    )

if __name__ == "__main__":
    main()
