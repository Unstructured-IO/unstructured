#! /usr/bin/env python3

import logging
import os
import sys
from typing import List, Optional, Tuple

import pandas as pd
from tqdm import tqdm

from unstructured.metrics.element_type import (
    calculate_element_type_percent_match,
    get_element_type_frequency,
)
from unstructured.metrics.text_extraction import calculate_accuracy, calculate_percent_missing_text
from unstructured.metrics.utils import (
    _display,
    _format_grouping_output,
    _listdir_recursive,
    _mean,
    _prepare_output_cct,
    _pstdev,
    _read_text_file,
    _stdev,
    _write_to_file,
)

logger = logging.getLogger("unstructured.eval")
handler = logging.StreamHandler()
handler.name = "eval_log_handler"
formatter = logging.Formatter("%(asctime)s %(processName)-10s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)

# Only want to add the handler once
if "eval_log_handler" not in [h.name for h in logger.handlers]:
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
    output_type: str = "json",
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
        logger.info("No output files to calculate to edit distances for, exiting")
        sys.exit(0)
    if output_type not in ["json", "txt"]:
        raise ValueError(
            f"Specified file type under `output_dir` or `output_list` should be one of \
                `json` or `txt`. The given file type is {output_type}, exiting."
        )
    if not all(_.endswith(output_type) for _ in output_list):
        logger.warning(
            "The directory contains file type inconsistent with the given input. \
                Please note that some files will be skipped."
        )

    rows = []
    ext_index = -(len(output_type) + 1)

    # assumption: output file name convention is name-of-file.doc.json
    # NOTE(klaijan) - disable=True means to not show, disable=False means to show the progress bar
    for doc in tqdm(output_list, leave=False, disable=not visualize):  # type: ignore
        # filename = (doc.split("/")[-1]).split(f".{output_type}")[0]
        filename = os.path.basename(doc)[:ext_index]
        doctype = filename.rsplit(".", 1)[-1]
        fn_txt = filename + ".txt"
        connector = doc.split("/")[0] if len(doc.split("/")) > 1 else None

        # not all odetta cct files follow the same naming convention;
        # some exclude the original filetype from the name
        if fn_txt not in source_list:
            fn = filename.rsplit(".", 1)[0]
            fn_txt = fn + ".txt"

        if fn_txt in source_list:  # type: ignore
            try:
                output_cct = _prepare_output_cct(os.path.join(output_dir, doc), output_type)
                source_cct = _read_text_file(os.path.join(source_dir, fn_txt))
            except Exception:
                # if any of the output/source file is unable to open, skip the loop
                continue
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
        connector = doc.split("/")[0] if len(doc.split("/")) > 1 else None

        if fn_json in source_list:  # type: ignore
            output = get_element_type_frequency(_read_text_file(os.path.join(output_dir, doc)))
            source = get_element_type_frequency(_read_text_file(os.path.join(source_dir, fn_json)))
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
