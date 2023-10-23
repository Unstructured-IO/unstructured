#! /usr/bin/env python3

import csv
import logging
import os
import statistics
from typing import Any, List, Optional, Tuple

import click

from unstructured.metrics.text_extraction import calculate_accuracy, calculate_percent_missing_text
from unstructured.staging.base import elements_from_json, elements_to_text

logger = logging.getLogger("unstructured.ingest")
handler = logging.StreamHandler()
handler.name = "ingest_log_handler"
formatter = logging.Formatter("%(asctime)s %(processName)-10s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)

# Only want to add the handler once
if "ingest_log_handler" not in [h.name for h in logger.handlers]:
    logger.addHandler(handler)

logger.setLevel(logging.DEBUG)


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
    default="metrics",
    help="Directory to save the output evaluation metrics to. Default to \
        [your_working_dir]/metrics/",
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
    """
    Loops through the list of structured output from all of `output_dir` or selected files from
    `output_list`, and compare with gold-standard of the same file name under `source_dir` or
    selected files from `source_list`.

    Calculates text accuracy and percent missing. After looped through the whole list, write to tsv.
    Also calculates the aggregated accuracy and percent missing.
    """
    if not output_list:
        output_list = _listdir_recursive(output_dir)
    if not source_list:
        source_list = _listdir_recursive(source_dir)

    rows = []
    accuracy_scores: List[float] = []
    percent_missing_scores: List[float] = []

    for doc in output_list:  # type: ignore
        fn = (doc.split("/")[-1]).split(".json")[0]
        fn_txt = fn + ".txt"
        connector = doc.split("/")[0]
        if fn_txt in source_list:  # type: ignore
            output_cct = elements_to_text(elements_from_json(os.path.join(output_dir, doc)))
            with open(f"{os.path.join(source_dir, fn_txt)}") as f:
                source_cct = f.read()
            accuracy = round(calculate_accuracy(output_cct, source_cct, weights), 3)
            percent_missing = round(calculate_percent_missing_text(output_cct, source_cct), 3)

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
    _display(agg_rows, headers)


def _listdir_recursive(dir: str):
    listdir = []
    for dirpath, _, filenames in os.walk(dir):
        for filename in filenames:
            # Remove the starting directory from the path to show the relative path
            relative_path = os.path.relpath(dirpath, dir)
            if relative_path == ".":
                listdir.append(filename)
            else:
                listdir.append(f"{relative_path}/{filename}")
    return listdir


def _write_to_file(dir: str, filename: str, rows: List[Any], headers: List[Any]):
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    with open(os.path.join(os.path.join(dir, filename)), "w", newline="") as tsv:
        writer = csv.writer(tsv, delimiter="\t")
        writer.writerow(headers)
        writer.writerows(rows)


def _display(rows, headers):
    col_widths = [
        max(len(headers[i]), max(len(str(row[i])) for row in rows)) for i in range(len(headers))
    ]
    click.echo(" ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers))))
    click.echo("-" * sum(col_widths) + "-" * (len(headers) - 1))
    for row in rows:
        formatted_row = []
        for item in row:
            if isinstance(item, float):
                formatted_row.append(f"{item:.3f}")
            else:
                formatted_row.append(str(item))
        click.echo(
            " ".join(formatted_row[i].ljust(col_widths[i]) for i in range(len(formatted_row))),
        )


def _mean(scores: List[float], rounding: Optional[int] = 3):
    if not rounding:
        return statistics.mean(scores)
    return round(statistics.mean(scores), rounding)


def _stdev(scores: List[float], rounding: Optional[int] = 3):
    if len(scores) <= 1:
        return None
    if not rounding:
        return statistics.stdev(scores)
    return round(statistics.stdev(scores), rounding)


def _pstdev(scores: List[float], rounding: Optional[int] = 3):
    if len(scores) <= 1:
        return None
    if not rounding:
        return statistics.pstdev(scores)
    return round(statistics.pstdev(scores), rounding)


if __name__ == "__main__":
    measure_edit_distance()
