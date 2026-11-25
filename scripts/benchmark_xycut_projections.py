import argparse
import ast
import gc
import json
import statistics
import subprocess
import time
from pathlib import Path

import numpy as np
from numba import njit

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import CoordinatesMetadata, ElementMetadata, Text
from unstructured.partition.utils import xycut
from unstructured.partition.utils.sorting import sort_page_elements

parser = argparse.ArgumentParser(
    description="Compare compiled XY-cut projections and public page sorting."
)
parser.add_argument(
    "--baseline-ref", required=True, help="Git revision to compare with the working tree"
)
args = parser.parse_args()
repository = Path(__file__).resolve().parents[1]
proposed = xycut.projection_by_bboxes
source = subprocess.check_output(
    [
        "git",
        "-C",
        str(repository),
        "show",
        f"{args.baseline_ref}:unstructured/partition/utils/xycut.py",
    ],
    text=True,
)
function = next(
    node
    for node in ast.parse(source).body
    if isinstance(node, ast.FunctionDef) and node.name == "projection_by_bboxes"
)
function.decorator_list = []
namespace = {"np": np}
exec(
    compile(ast.Module(body=[function], type_ignores=[]), "<baseline-projection>", "exec"),
    namespace,
)
baseline = njit(namespace["projection_by_bboxes"])


def paired(label, call, check):
    outputs = []
    times = {"base": [], "fixed": []}
    for index in range(9):
        for name, function in (
            [("base", baseline), ("fixed", proposed)]
            if index % 2 == 0
            else [("fixed", proposed), ("base", baseline)]
        ):
            xycut.projection_by_bboxes = function
            gc.collect()
            started = time.perf_counter()
            output = call(function)
            elapsed = (time.perf_counter() - started) * 1000
            if index > 1:
                times[name].append(elapsed)
            outputs.append(check(output))
    assert all(value == outputs[0] for value in outputs)
    print(
        json.dumps(
            {
                "case": label,
                "median_ms": {name: statistics.median(values) for name, values in times.items()},
                "samples": times,
            }
        ),
        flush=True,
    )


datasets = {}
for count, width in [(20, 2000), (500, 2000), (5000, 4000)]:
    datasets[f"overlap-{count}-{width}"] = np.array(
        [[index % 30, index % 50, width - index % 30, 100 + index % 50] for index in range(count)]
    )
datasets["two-columns-600"] = np.array(
    [[(i % 2) * 1000, (i // 2) * 30, (i % 2) * 1000 + 800, (i // 2) * 30 + 20] for i in range(600)]
)
datasets["sparse-20"] = np.array(
    [[i * 1000, i * 1000, i * 1000 + 20, i * 1000 + 20] for i in range(20)]
)
for label, boxes in datasets.items():
    paired(f"projection-{label}", lambda f: f(boxes, 0), lambda out: out.tolist())
    elements = [
        Text(
            str(index),
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    ((x0, y0), (x0, y1), (x1, y1), (x1, y0)), PixelSpace(20000, 20000)
                )
            ),
        )
        for index, (x0, y0, x1, y1) in enumerate(boxes)
    ]
    for direction in ("x", "y"):
        paired(
            f"sort-page-{label}-{direction}",
            lambda _: sort_page_elements(elements, xy_cut_primary_direction=direction),
            lambda out: [e.text for e in out],
        )
xycut.projection_by_bboxes = proposed
