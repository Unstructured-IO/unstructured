#! /usr/bin/env python3

import logging
import os
import statistics
import sys
from typing import List, Optional, Tuple, Union

import click
import pandas as pd
from tqdm import tqdm

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


agg_headers = ["metric", "average", "sample_sd", "population_sd", "count"]


def measure_text_extraction_accuracy(
    output_dir: str,
    source_dir: str,
    output_list: Optional[List[str]] = None,
    source_list: Optional[List[str]] = None,
    export_dir: str = "metrics",
    grouping: Optional[str] = None,
    weights: Tuple[int, int, int] = (2, 1, 1),
    visualize: bool = False,
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

    # assumption: output file name convention is name-of-file.doc.json
    # NOTE(klaijan) - disable=True means to not show, disable=False means to show the progress bar
    for doc in tqdm(output_list, leave=False, disable=not visualize):  # type: ignore
        filename = (doc.split("/")[-1]).split(".json")[0]
        doctype = filename.rsplit(".", 1)[-1]
        fn_txt = filename + ".txt"
        connector = doc.split("/")[0]

        # not all odetta cct files follow the same naming convention;
        # some exclude the original filetype from the name
        if fn_txt not in source_list:
            fn = filename.rsplit(".", 1)[0]
            fn_txt = fn + ".txt"

        if fn_txt in source_list:  # type: ignore
            output_cct = elements_to_text(elements_from_json(os.path.join(output_dir, doc)))
            source_cct = _read_text(os.path.join(source_dir, fn_txt))
            accuracy = round(calculate_accuracy(output_cct, source_cct, weights), 3)
            percent_missing = round(calculate_percent_missing_text(output_cct, source_cct), 3)

            rows.append([filename, doctype, connector, accuracy, percent_missing])

    headers = ["filename", "doctype", "connector", "cct-accuracy", "cct-%missing"]
    df = pd.DataFrame(rows, columns=headers)
    export_filename = "all-docs-cct"

    acc = df[["cct-accuracy"]].agg([_mean, _stdev, _pstdev, "count"]).transpose()
    miss = df[["cct-%missing"]].agg([_mean, _stdev, _pstdev, "count"]).transpose()
    agg_df = pd.concat((acc, miss)).reset_index()
    agg_df.columns = agg_headers

    if grouping:
        if grouping in ["doctype", "connector"]:
            grouped_acc = (
                df.groupby(grouping)
                .agg({"cct-accuracy": [_mean, _stdev, "count"]})
                .rename(columns={"_mean": "mean", "_stdev": "stdev"})
            )
            grouped_miss = (
                df.groupby(grouping)
                .agg({"cct-%missing": [_mean, _stdev, "count"]})
                .rename(columns={"_mean": "mean", "_stdev": "stdev"})
            )
            df = _format_grouping_output(grouped_acc, grouped_miss)
            export_filename = f"all-{grouping}-agg-cct"
        else:
            print("No field to group by. Returning a non-group evaluation.")

    _write_to_file(export_dir, f"{export_filename}.tsv", df)
    _write_to_file(export_dir, "aggregate-scores-cct.tsv", agg_df)
    _display(agg_df)


def measure_element_type_accuracy(
    output_dir: str,
    source_dir: str,
    output_list: Optional[List[str]] = None,
    source_list: Optional[List[str]] = None,
    export_dir: str = "metrics",
    visualize: bool = False,
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

    # NOTE(klaijan) - disable=True means to not show, disable=False means to show the progress bar
    for doc in tqdm(output_list, leave=False, disable=not visualize):  # type: ignore
        filename = (doc.split("/")[-1]).split(".json")[0]
        doctype = filename.rsplit(".", 1)[-1]
        fn_json = filename + ".json"
        connector = doc.split("/")[0]
        if fn_json in source_list:  # type: ignore
            output = get_element_type_frequency(_read_text(os.path.join(output_dir, doc)))
            source = get_element_type_frequency(_read_text(os.path.join(source_dir, fn_json)))
            accuracy = round(calculate_element_type_percent_match(output, source), 3)
            rows.append([filename, doctype, connector, accuracy])

    headers = ["filename", "doctype", "connector", "element-type-accuracy"]
    df = pd.DataFrame(rows, columns=headers)
    if df.empty:
        agg_df = pd.DataFrame(["element-type-accuracy", None, None, None, 0]).transpose()
    else:
        agg_df = df.agg({"element-type-accuracy": [_mean, _stdev, _pstdev, "count"]}).transpose()
        agg_df = agg_df.reset_index()
    agg_df.columns = agg_headers

    _write_to_file(export_dir, "all-docs-element-type-frequency.tsv", df)
    _write_to_file(export_dir, "aggregate-scores-element-type.tsv", agg_df)
    _display(agg_df)


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


def _format_grouping_output(*df):
    return pd.concat(df, axis=1).reset_index()


def _display(df):
    if len(df) == 0:
        return
    headers = df.columns.tolist()
    col_widths = [
        max(len(header), max(len(str(item)) for item in df[header])) for header in headers
    ]
    click.echo(" ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers)))
    click.echo("-" * sum(col_widths) + "-" * (len(headers) - 1))
    for _, row in df.iterrows():
        formatted_row = []
        for item in row:
            if isinstance(item, float):
                formatted_row.append(f"{item:.3f}")
            else:
                formatted_row.append(str(item))
        click.echo(
            " ".join(formatted_row[i].ljust(col_widths[i]) for i in range(len(formatted_row))),
        )


def _write_to_file(dir: str, filename: str, df: pd.DataFrame, mode: str = "w"):
    if mode not in ["w", "a"]:
        raise ValueError("Mode not supported. Mode must be one of [w, a].")
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
    if "count" in df.columns:
        df["count"] = df["count"].astype(int)
    if "filename" in df.columns and "connector" in df.columns:
        df.sort_values(by=["connector", "filename"], inplace=True)
    df.to_csv(os.path.join(dir, filename), sep="\t", mode=mode, index=False, header=(mode == "w"))


def _mean(scores: Union[pd.Series, List[float]], rounding: Optional[int] = 3):
    if len(scores) == 0:
        return None
    mean = statistics.mean(scores)
    if not rounding:
        return mean
    return round(mean, rounding)


def _stdev(scores: List[Optional[float]], rounding: Optional[int] = 3):
    # Filter out None values
    scores = [score for score in scores if score is not None]
    # Proceed only if there are more than one value
    if len(scores) <= 1:
        return None
    if not rounding:
        return statistics.stdev(scores)
    return round(statistics.stdev(scores), rounding)


def _pstdev(scores: List[Optional[float]], rounding: Optional[int] = 3):
    scores = [score for score in scores if score is not None]
    if len(scores) <= 1:
        return None
    if not rounding:
        return statistics.pstdev(scores)
    return round(statistics.pstdev(scores), rounding)


def _read_text(path):
    with open(path, errors="ignore") as f:
        text = f.read()
    return text
