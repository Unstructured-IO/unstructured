"""Compare public chunking with current and baseline metadata consolidation.

Run from the repository root, for example:
python scripts/benchmark_chunk_metadata.py --baseline-ref <commit-before-the-change>
"""

import argparse
import ast
import gc
import json
import statistics
import subprocess
import time
from functools import cached_property
from typing import cast

from unstructured.chunking import base
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import ElementMetadata, Text


def baseline_property(ref):
    source = subprocess.check_output(
        ["git", "show", f"{ref}:unstructured/chunking/base.py"], text=True
    )
    cls = next(
        item
        for item in ast.parse(source).body
        if isinstance(item, ast.ClassDef) and item.name == "_Chunker"
    )
    method = next(
        item
        for item in cls.body
        if isinstance(item, ast.FunctionDef) and item.name == "_meta_kwargs"
    )
    namespace = {**vars(base), "cast": cast}
    exec(compile(ast.Module(body=[method], type_ignores=[]), "<baseline>", "exec"), namespace)
    return namespace["_meta_kwargs"]


def fixture(count, width, provenance):
    return [
        Text(
            "x",
            element_id=f"source-{i}",
            metadata=ElementMetadata(
                link_texts=[f"label-{i}-{j}" for j in range(width)],
                link_urls=[f"https://example.com/{i}/{j}" for j in range(width)],
                emphasized_text_contents=[f"emphasis-{i}-{j}" for j in range(width)],
                emphasized_text_tags=["b"] * width,
                enrichment_origins=(
                    {"text": [{"type": "ocr", "provider": "fixture", "model": f"model-{i}"}]}
                    if provenance
                    else None
                ),
            ),
        )
        for i in range(count)
    ]


def run(elements, prop, include_orig_elements):
    prop.__set_name__(base._Chunker, "_meta_kwargs")
    base._Chunker._meta_kwargs = prop
    gc.collect()
    start = time.perf_counter()
    chunks = chunk_elements(
        elements, max_characters=10000, include_orig_elements=include_orig_elements
    )
    duration = (time.perf_counter() - start) * 1000
    result = [chunk.to_dict() for chunk in chunks]
    for item in result:
        item.pop("element_id")  # Each new chunk gets a fresh generated UUID.
    return duration, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    args = parser.parse_args()
    current = base._Chunker._meta_kwargs
    previous = baseline_property(args.baseline_ref)
    assert isinstance(current, cached_property)
    assert isinstance(previous, cached_property)
    try:
        for count, width, provenance, originals in [
            (20, 1, False, False),
            (500, 16, False, False),
            (2000, 32, False, False),
            (2000, 0, True, False),
            (500, 16, True, True),
        ]:
            elements = fixture(count, width, provenance)
            results = {"baseline": [], "current": []}
            for iteration in range(9):
                order = [("baseline", previous), ("current", current)]
                if iteration % 2:
                    order.reverse()
                outputs = []
                for name, prop in order:
                    duration, output = run(elements, prop, originals)
                    outputs.append(output)
                    if iteration >= 2:
                        results[name].append(duration)
                assert outputs[0] == outputs[1], "public chunk output changed"
            print(
                json.dumps(
                    {
                        "elements": count,
                        "items_per_list": width,
                        "unique_provenance": provenance,
                        "include_orig_elements": originals,
                        "median_ms": {
                            name: statistics.median(values) for name, values in results.items()
                        },
                        "samples_ms": results,
                    }
                ),
                flush=True,
            )
    finally:
        base._Chunker._meta_kwargs = current


if __name__ == "__main__":
    main()
