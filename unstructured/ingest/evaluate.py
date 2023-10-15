#! /usr/bin/env python3

import csv
import os
import statistics
from typing import List, Optional, Tuple

import click

from unstructured.metrics.text_extraction import calculate_accuracy, calculate_percent_missing_text
from unstructured.staging.base import elements_from_json, elements_to_text


@click.command()
@click.option("--output_dir", type=click.STRING, help="Directory to a structured output.")
@click.option(
    "--output_list",
    type=click.STRING,
    multiple=True,
    help="Optional: list of selected structured output file names under the \
        directory to be evaluate. If none, all files under directory will be use.",
)
@click.option("--source_dir", type=click.STRING, help="Directory to a cct source.")
@click.option(
    "--source_list",
    type=click.STRING,
    multiple=True,
    help="Optional: list of selected cct source file names under the directory \
        to be evaluate. If none, all files under directory will be use.",
)
@click.option(
    "--export_dir",
    type=click.STRING,
    default="evaluation-metrics",
    help="Directory to save the output evaluation metrics to. Default to \
        [your_working_dir]/evaluation_metrics/",
)
@click.option(
    "--weights",
    type=(click.INT, click.INT, click.INT),
    default=(2, 1, 1),
    show_default=True,
    help="A tuple of weights to the Levenshtein distance calculation. \
        See text_extraction.py/calculate_edit_distance for more details.",
)
def measure_edit_distance(
    output_dir: str,
    output_list: Optional[List[str]],
    source_dir: str,
    source_list: Optional[List[str]],
    export_dir: str,
    weights: Tuple[int, int, int],
) -> None:
    if not output_list:
        output_list = os.listdir(f"{output_dir}")
    if not source_list:
        source_list = os.listdir(f"{source_dir}")

    rows = []
    accuracy_scores: List[float] = []
    percent_missing_scores: List[float] = []

    for doc in output_list:
        fn = (doc.split("/")[-1]).split(".json")[0]
        fn_txt = fn + ".txt"
        connector = doc.split("/")[0]
        if fn_txt in source_list:
            output_cct = elements_to_text(elements_from_json(os.path.join(output_dir, doc)))
            with open(f"{os.path.join(source_dir, fn_txt)}") as f:
                source_cct = f.read()
            accuracy = calculate_accuracy(output_cct, source_cct, weights)
            percent_missing = calculate_percent_missing_text(output_cct, source_cct)

            rows.append([fn, connector, accuracy, percent_missing])
            accuracy_scores.append(accuracy)
            percent_missing_scores.append(percent_missing)

    headers = ["filename", "connector", "cct-accuracy", "cct-%missing"]
    _write_to_file(export_dir, "all-docs-cct.tsv", rows, headers)

    headers = ["strategy", "average", "sample_sd", "population_sd", "count"]
    agg_rows = []
    agg_rows.append(
        [
            "cct-accuracy",
            _mean(accuracy_scores),
            _stdev(accuracy_scores),
            _pstdev(accuracy_scores),
            len(accuracy_scores),
        ],
    )
    agg_rows.append(
        [
            "cct-%missing",
            _mean(percent_missing_scores),
            _stdev(percent_missing_scores),
            _pstdev(percent_missing_scores),
            len(percent_missing_scores),
        ],
    )
    _write_to_file(export_dir, "aggregate-scores-cct.tsv", agg_rows, headers)


def _write_to_file(dir, filename, rows, headers):
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    with open(os.path.join(os.path.join(dir, filename)), "w", newline="") as tsv:
        writer = csv.writer(tsv, delimiter="\t")
        writer.writerow(headers)
        writer.writerows(rows)


def _mean(scores):
    return statistics.mean(scores)


def _stdev(scores):
    if len(scores) <= 1:
        return None
    return statistics.stdev(scores)


def _pstdev(scores):
    if len(scores) <= 1:
        return None
    return statistics.pstdev(scores)


if __name__ == "__main__":
    measure_edit_distance()
