#! /usr/bin/env python3

import csv
import logging
import os
import statistics
import sys
from typing import Any, List, Optional, Tuple

import click

from unstructured.metrics.element_type import (
    calculate_element_type_percent_match,
    get_element_type_frequency,
)
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


agg_headers = ["strategy", "average", "sample_sd", "population_sd", "count"]


@click.group()
def main():
    pass


@main.command()
@click.option("--output_dir", type=str, help="Directory to structured output.")
@click.option(
    "--output_list",
    type=str,
    multiple=True,
    help="Optional: list of selected structured output file names under the \
        directory to be evaluate. If none, all files under directory will be use.",
)
@click.option("--source_dir", type=str, help="Directory to source.")
@click.option(
    "--source_list",
    type=str,
    multiple=True,
    help="Optional: list of selected source file names under the directory \
        to be evaluate. If none, all files under directory will be use.",
)
@click.option(
    "--export_dir",
    type=str,
    default="metrics",
    help="Directory to save the output evaluation metrics to. Default to \
        your/working/dir/metrics/",
)
@click.option(
    "--weights",
    type=(int, int, int),
    default=(2, 1, 1),
    show_default=True,
    help="A tuple of weights to the Levenshtein distance calculation. \
        See text_extraction.py/calculate_edit_distance for more details.",
)
def measure_text_edit_distance(
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

    if not output_list:
        print("No output files to calculate to edit distances for, exiting")
        sys.exit(0)

    rows = []
    accuracy_scores: List[float] = []
    percent_missing_scores: List[float] = []

    # assumption: output file name convention is name-of-file.doc.json
    for doc in output_list:  # type: ignore
        fn = (doc.split("/")[-1]).split(".json")[0]
        doctype = fn.rsplit(".", 1)[-1]
        fn_txt = fn + ".txt"
        connector = doc.split("/")[0]

        if fn_txt in source_list:  # type: ignore
            output_cct = elements_to_text(elements_from_json(os.path.join(output_dir, doc)))
            source_cct = _read_text(os.path.join(source_dir, fn_txt))
            accuracy = round(calculate_accuracy(output_cct, source_cct, weights), 3)
            percent_missing = round(calculate_percent_missing_text(output_cct, source_cct), 3)

            rows.append([fn, doctype, connector, accuracy, percent_missing])
            accuracy_scores.append(accuracy)
            percent_missing_scores.append(percent_missing)

    headers = ["filename", "doctype", "connector", "cct-accuracy", "cct-%missing"]
    _write_to_file(export_dir, "all-docs-cct.tsv", rows, headers)

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
    _write_to_file(export_dir, "aggregate-scores-cct.tsv", agg_rows, agg_headers)
    _display(agg_rows, agg_headers)


@main.command()
@click.option("--output_dir", type=str, help="Directory to structured output.")
@click.option(
    "--output_list",
    type=str,
    multiple=True,
    help="Optional: list of selected structured output file names under the \
        directory to be evaluate. If none, all files under directory will be used.",
)
@click.option("--source_dir", type=str, help="Directory to structured source.")
@click.option(
    "--source_list",
    type=str,
    multiple=True,
    help="Optional: list of selected source file names under the directory \
        to be evaluate. If none, all files under directory will be used.",
)
@click.option(
    "--export_dir",
    type=str,
    default="metrics",
    help="Directory to save the output evaluation metrics to. Default to \
        your/working/dir/metrics/",
)
def measure_element_type_accuracy(
    output_dir: str,
    output_list: Optional[List[str]],
    source_dir: str,
    source_list: Optional[List[str]],
    export_dir: str,
):
    """
    Loops through the list of structured output from all of `output_dir` or selected files from
    `output_list`, and compare with gold-standard of the same file name under `source_dir` or
    selected files from `source_list`.

    Calculates element type frequency accuracy and percent missing. After looped through the
    whole list, write to tsv. Also calculates the aggregated accuracy.
    """
    if not output_list:
        output_list = _listdir_recursive(output_dir)
    if not source_list:
        source_list = _listdir_recursive(source_dir)

    rows = []
    accuracy_scores: List[float] = []

    for doc in output_list:  # type: ignore
        fn = (doc.split("/")[-1]).split(".json")[0]
        doctype = fn.rsplit(".", 1)[-1]
        connector = doc.split("/")[0]
        if doc in source_list:  # type: ignore
            output = get_element_type_frequency(_read_text(os.path.join(output_dir, doc)))
            source = get_element_type_frequency(_read_text(os.path.join(source_dir, doc)))
            accuracy = round(calculate_element_type_percent_match(output, source), 3)
            rows.append([fn, doctype, connector, accuracy])
            accuracy_scores.append(accuracy)

    headers = ["filename", "doctype", "connector", "element-type-accuracy"]
    _write_to_file(export_dir, "all-docs-element-type-frequency.tsv", rows, headers)

    agg_rows = []
    agg_rows.append(
        [
            "element-type-accuracy",
            _mean(accuracy_scores),
            _stdev(accuracy_scores),
            _pstdev(accuracy_scores),
            len(accuracy_scores),
        ],
    )
    _write_to_file(export_dir, "aggregate-scores-element-type.tsv", agg_rows, agg_headers)
    _display(agg_rows, agg_headers)


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


def _write_to_file(dir: str, filename: str, rows: List[Any], headers: List[Any], mode: str = "w"):
    if mode not in ["w", "a"]:
        raise ValueError("Mode not supported. Mode must be one of [w, a].")
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    with open(os.path.join(os.path.join(dir, filename)), mode, newline="") as tsv:
        writer = csv.writer(tsv, delimiter="\t")
        if mode == "w":
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
    if len(scores) < 1:
        return None
    elif len(scores) == 1:
        mean = scores[0]
    else:
        mean = statistics.mean(scores)
    if not rounding:
        return mean
    return round(mean, rounding)


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


def _read_text(path):
    with open(path, errors="ignore") as f:
        text = f.read()
    return text


if __name__ == "__main__":
    main()
