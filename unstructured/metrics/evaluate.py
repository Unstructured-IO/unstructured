#! /usr/bin/env python3

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pandas as pd
from tqdm import tqdm

from unstructured.metrics.element_type import (
    calculate_element_type_percent_match,
    get_element_type_frequency,
)
from unstructured.metrics.table.table_eval import TableEvalProcessor
from unstructured.metrics.text_extraction import calculate_accuracy, calculate_percent_missing_text
from unstructured.metrics.utils import (
    _count,
    _display,
    _format_grouping_output,
    _listdir_recursive,
    _mean,
    _prepare_output_cct,
    _pstdev,
    _read_text_file,
    _rename_aggregated_columns,
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

    acc = df[["cct-accuracy"]].agg([_mean, _stdev, _pstdev, _count]).transpose()
    miss = df[["cct-%missing"]].agg([_mean, _stdev, _pstdev, _count]).transpose()
    if acc.shape[1] == 0 and miss.shape[1] == 0:
        agg_df = pd.DataFrame(columns=agg_headers)
    else:
        agg_df = pd.concat((acc, miss)).reset_index()
        agg_df.columns = agg_headers

    _write_to_file(export_dir, "all-docs-cct.tsv", df)
    _write_to_file(export_dir, "aggregate-scores-cct.tsv", agg_df)

    if grouping:
        get_mean_grouping(grouping, df, export_dir, "text_extraction")

    _display(agg_df)


def measure_element_type_accuracy(
    output_dir: str,
    source_dir: str,
    output_list: Optional[List[str]] = None,
    source_list: Optional[List[str]] = None,
    export_dir: str = "metrics",
    grouping: Optional[str] = None,
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

    if grouping:
        get_mean_grouping(grouping, df, export_dir, "element_type")

    _display(agg_df)


def get_mean_grouping(
    grouping: str, data_input: Union[pd.DataFrame, str], export_dir: str, eval_name: str
) -> None:
    """Aggregates accuracy and missing metrics by 'doctype' or 'connector', exporting to TSV.

    Args:
        grouping (str): Grouping category ('doctype' or 'connector').
        data_input (Union[pd.DataFrame, str]): DataFrame or path to a CSV/TSV file.
        export_dir (str): Directory for the exported TSV file.
        eval_name (str): Evaluated metric ('text_extraction' or 'element_type').
    """
    if grouping not in ("doctype", "connector"):
        raise ValueError("Invalid grouping category. Returning a non-group evaluation.")
    if isinstance(data_input, str):
        if not os.path.exists(data_input):
            raise FileNotFoundError(f"File {data_input} not found.")
        if data_input.endswith(".csv"):
            df = pd.read_csv(data_input)
        elif data_input.endswith((".tsv", ".txt")):
            df = pd.read_csv(data_input, sep="\t")
        else:
            raise ValueError("Please provide a .csv or .tsv file.")
    else:
        df = data_input
    if df.empty or grouping not in df.columns or df[grouping].isnull().all():
        raise SystemExit(
            f"Data cannot be aggregated by `{grouping}`."
            f" Check if it's empty or the column is missing/empty."
        )
    if eval_name == "text_extraction":
        grouped_acc = _rename_aggregated_columns(
            df.groupby(grouping).agg({"cct-accuracy": [_mean, _stdev, _count]})
        )
        grouped_miss = _rename_aggregated_columns(
            df.groupby(grouping).agg({"cct-%missing": [_mean, _stdev, _count]})
        )
        grouped_df = _format_grouping_output(grouped_acc, grouped_miss)
        eval_name = "cct"
    elif eval_name == "element_type":
        grouped_df = _rename_aggregated_columns(
            df.groupby(grouping).agg({"element-type-accuracy": [_mean, _stdev, _count]})
        )
        grouped_df = _format_grouping_output(grouped_df)
        eval_name = "element-type"
    else:
        raise ValueError("Unknown metric. Expected `text_extraction` or `element_type`.")
    _write_to_file(export_dir, f"all-{grouping}-agg-{eval_name}.tsv", grouped_df)


def measure_table_structure_accuracy(
    output_dir: str,
    source_dir: str,
    output_list: Optional[List[str]] = None,
    source_list: Optional[List[str]] = None,
    export_dir: str = "metrics",
    visualize: bool = False,
    cutoff: Optional[float] = None,
):
    """
    Loops through the list of structured output from all of `output_dir` or selected files from
    `output_list`, and compare with gold-standard of the same file name under `source_dir` or
    selected files from `source_list`. Supports also a json file with filenames as keys and
    structured gold-standard output as values.

    Calculates:
        - table found accuracy
        - element in column index accuracy
        - element in row index accuracy
        - element's column content accuracy
        - element's row content accuracy

    After looped through the whole list, write to tsv. Also calculates the aggregated accuracy.
    """
    if not output_list:
        output_list = _listdir_recursive(output_dir)
    if not source_list:
        source_list = _listdir_recursive(source_dir)

    rows = []
    for doc in tqdm(output_list, leave=False, disable=not visualize):  # type: ignore
        doc_path = Path(doc)
        out_filename = doc_path.stem
        doctype = Path(out_filename).suffix
        src_gt_filename = out_filename + ".json"
        connector = doc_path.parts[-2] if len(doc_path.parts) > 1 else None

        if src_gt_filename in source_list:  # type: ignore
            prediction_file = Path(output_dir) / doc
            if not prediction_file.exists():
                logger.warning(f"Prediction file {prediction_file} does not exist, skipping")
                continue

            ground_truth_file = Path(source_dir) / src_gt_filename
            if not ground_truth_file.exists():
                logger.warning(f"Ground truth file {ground_truth_file} does not exist, skipping")
                continue

            processor = TableEvalProcessor.from_json_files(
                prediction_file=prediction_file,
                ground_truth_file=ground_truth_file,
                cutoff=cutoff,
            )
            report = processor.process_file()
            rows.append(
                [
                    out_filename,
                    doctype,
                    connector,
                    report.total_tables,
                    report.table_level_acc,
                    report.element_col_level_index_acc,
                    report.element_row_level_index_acc,
                    report.element_col_level_content_acc,
                    report.element_row_level_content_acc,
                ]
            )

    headers = [
        "filename",
        "doctype",
        "connector",
        "total_tables",
        "table_level_acc",
        "element_col_level_index_acc",
        "element_row_level_index_acc",
        "element_col_level_content_acc",
        "element_row_level_content_acc",
    ]
    df = pd.DataFrame(rows, columns=headers)
    has_tables_df = df[df["total_tables"] > 0]

    if has_tables_df.empty:
        agg_df = pd.DataFrame(
            [
                ["total_tables", None, None, None, 0],
                ["table_level_acc", None, None, None, 0],
                ["element_col_level_index_acc", None, None, None, 0],
                ["element_row_level_index_acc", None, None, None, 0],
                ["element_col_level_content_acc", None, None, None, 0],
                ["element_row_level_content_acc", None, None, None, 0],
            ]
        ).reset_index()
    else:
        element_metrics_results = {}
        for metric in [
            "total_tables",
            "table_level_acc",
            "element_col_level_index_acc",
            "element_row_level_index_acc",
            "element_col_level_content_acc",
            "element_row_level_content_acc",
        ]:
            metric_df = has_tables_df[has_tables_df[metric].notnull()]
            agg_metric = metric_df[metric].agg([_mean, _stdev, _pstdev, _count]).transpose()
            if agg_metric.empty:
                element_metrics_results[metric] = pd.Series(
                    data=[None, None, None, 0], index=["_mean", "_stdev", "_pstdev", "_count"]
                )
            else:
                element_metrics_results[metric] = agg_metric
        agg_df = pd.DataFrame(element_metrics_results).transpose().reset_index()

    agg_df.columns = agg_headers
    _write_to_file(
        export_dir, "all-docs-table-structure-accuracy.tsv", _rename_aggregated_columns(df)
    )
    _write_to_file(
        export_dir, "aggregate-table-structure-accuracy.tsv", _rename_aggregated_columns(agg_df)
    )
    _display(agg_df)
