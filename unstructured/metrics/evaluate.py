#! /usr/bin/env python3

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pandas as pd
from tqdm import tqdm

from unstructured.metrics.element_type import (
    calculate_element_type_percent_match,
    get_element_type_frequency,
)
from unstructured.metrics.object_detection import (
    ObjectDetectionEvalProcessor,
)
from unstructured.metrics.table.table_eval import TableEvalProcessor
from unstructured.metrics.text_extraction import calculate_accuracy, calculate_percent_missing_text
from unstructured.metrics.utils import (
    _count,
    _display,
    _format_grouping_output,
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

AGG_HEADERS = ["metric", "average", "sample_sd", "population_sd", "count"]
AGG_HEADERS_MAPPING = {
    "index": "metric",
    "_mean": "average",
    "_stdev": "sample_sd",
    "_pstdev": "population_sd",
    "_count": "count",
}
OUTPUT_TYPE_OPTIONS = ["json", "txt"]


@dataclass
class BaseMetricsCalculator(ABC):
    """Foundation class for specialized metrics calculators.

    It provides a common interface for calculating metrics based on outputs and ground truths.
    Those can be provided as either directories or lists of files.
    """

    documents_dir: str | Path
    ground_truths_dir: str | Path

    def __post_init__(self):
        """Discover all files in the provided directories."""
        self.documents_dir = Path(self.documents_dir).resolve()
        self.ground_truths_dir = Path(self.ground_truths_dir).resolve()

        # -- auto-discover all files in the directories --
        self._document_paths = [
            path.relative_to(self.documents_dir)
            for path in self.documents_dir.glob("*")
            if path.is_file()
        ]
        self._ground_truth_paths = [
            path.relative_to(self.ground_truths_dir)
            for path in self.ground_truths_dir.glob("*")
            if path.is_file()
        ]

    @property
    @abstractmethod
    def default_tsv_name(self):
        """Default name for the per-document metrics TSV file."""

    @property
    @abstractmethod
    def default_agg_tsv_name(self):
        """Default name for the aggregated metrics TSV file."""

    @abstractmethod
    def _generate_dataframes(self, rows: list) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Generates pandas DataFrames from the list of rows.

        The first DF (index 0) is a dataframe containing metrics per file.
        The second DF (index 1) is a dataframe containing the aggregated
            metrics.
        """

    def on_files(
        self,
        document_paths: Optional[list[str | Path]] = None,
        ground_truth_paths: Optional[list[str | Path]] = None,
    ) -> BaseMetricsCalculator:
        """Overrides the default list of files to process."""
        if document_paths:
            self._document_paths = [Path(p) for p in document_paths]

        if ground_truth_paths:
            self._ground_truth_paths = [Path(p) for p in ground_truth_paths]

        return self

    def calculate(
        self,
        executor: Optional[concurrent.futures.Executor] = None,
        export_dir: Optional[str | Path] = None,
        visualize_progress: bool = True,
        display_agg_df: bool = True,
    ) -> pd.DataFrame:
        """Calculates metrics for each document using the provided executor.

        * Optionally, the results can be exported and displayed.
        * It loops through the list of structured output from all of `documents_dir` or
        selected files from `document_paths`, and compares them with gold-standard
        of the same file name under `ground_truths_dir` or selected files from `ground_truth_paths`.

        Args:
            executor: concurrent.futures.Executor instance
            export_dir: directory to export the results
            visualize_progress: whether to display progress bar
            display_agg_df: whether to display the aggregated results

        Returns:
            Metrics for each document as a pandas DataFrame
        """
        if executor is None:
            executor = self._default_executor()
        rows = self._process_all_documents(executor, visualize_progress)
        df, agg_df = self._generate_dataframes(rows)

        if export_dir is not None:
            _write_to_file(export_dir, self.default_tsv_name, df)
            _write_to_file(export_dir, self.default_agg_tsv_name, agg_df)

        if display_agg_df is True:
            _display(agg_df)
        return df

    @classmethod
    def _default_executor(cls):
        max_processors = int(os.environ.get("MAX_PROCESSES", os.cpu_count()))
        logger.info(f"Configuring a pool of {max_processors} processors for parallel processing.")
        return cls._get_executor_class()(max_workers=max_processors)

    @classmethod
    def _get_executor_class(
        cls,
    ) -> type[concurrent.futures.ThreadPoolExecutor] | type[concurrent.futures.ProcessPoolExecutor]:
        return concurrent.futures.ProcessPoolExecutor

    def _process_all_documents(
        self, executor: concurrent.futures.Executor, visualize_progress: bool
    ) -> list:
        """Triggers processing of all documents using the provided executor.

        Failures are omitted from the returned result.
        """
        with executor:
            return [
                row
                for row in tqdm(
                    executor.map(self._try_process_document, self._document_paths),
                    total=len(self._document_paths),
                    leave=False,
                    disable=not visualize_progress,
                )
                if row is not None
            ]

    def _try_process_document(self, doc: Path) -> Optional[list]:
        """Safe wrapper around the document processing method."""
        logger.info(f"Processing {doc}")
        try:
            return self._process_document(doc)
        except Exception as e:
            logger.error(f"Failed to process document {doc}: {e}")
            return None

    @abstractmethod
    def _process_document(self, doc: Path) -> Optional[list]:
        """Should return all metadata and metrics for a single document."""


@dataclass
class TableStructureMetricsCalculator(BaseMetricsCalculator):
    """Calculates the following metrics for tables:
        - tables found accuracy
        - table-level accuracy
        - element in column index accuracy
        - element in row index accuracy
        - element's column content accuracy
        - element's row content accuracy
    It also calculates the aggregated accuracy.
    """

    cutoff: Optional[float] = None

    def __post_init__(self):
        super().__post_init__()

    @property
    def supported_metric_names(self):
        return [
            "total_tables",
            "table_level_acc",
            "table_detection_recall",
            "table_detection_precision",
            "table_detection_f1",
            "composite_structure_acc",
            "element_col_level_index_acc",
            "element_row_level_index_acc",
            "element_col_level_content_acc",
            "element_row_level_content_acc",
        ]

    @property
    def default_tsv_name(self):
        return "all-docs-table-structure-accuracy.tsv"

    @property
    def default_agg_tsv_name(self):
        return "aggregate-table-structure-accuracy.tsv"

    def _process_document(self, doc: Path) -> Optional[list]:
        doc_path = Path(doc)
        out_filename = doc_path.stem
        doctype = Path(out_filename).suffix[1:]
        src_gt_filename = out_filename + ".json"
        connector = doc_path.parts[-2] if len(doc_path.parts) > 1 else None

        if src_gt_filename in self._ground_truth_paths:  # type: ignore
            return None

        prediction_file = self.documents_dir / doc
        if not prediction_file.exists():
            logger.warning(f"Prediction file {prediction_file} does not exist, skipping")
            return None

        ground_truth_file = self.ground_truths_dir / src_gt_filename
        if not ground_truth_file.exists():
            logger.warning(f"Ground truth file {ground_truth_file} does not exist, skipping")
            return None

        processor_from_text_as_html = TableEvalProcessor.from_json_files(
            prediction_file=prediction_file,
            ground_truth_file=ground_truth_file,
            cutoff=self.cutoff,
            source_type="html",
        )
        report_from_html = processor_from_text_as_html.process_file()
        return [
            out_filename,
            doctype,
            connector,
            report_from_html.total_predicted_tables,
        ] + [getattr(report_from_html, metric) for metric in self.supported_metric_names]

    def _generate_dataframes(self, rows):
        headers = [
            "filename",
            "doctype",
            "connector",
            "total_predicted_tables",
        ] + self.supported_metric_names

        df = pd.DataFrame(rows, columns=headers)
        df["_table_weights"] = df["total_tables"]
        # we give false positive tables a 1 table worth of weight in computing table level acc
        df["_table_weights"][df.total_tables.eq(0) & df.total_predicted_tables.gt(0)] = 1
        # filter down to only those with actual and/or predicted tables
        has_tables_df = df[df["_table_weights"] > 0]

        if has_tables_df.empty:
            agg_df = pd.DataFrame(
                [[metric, None, None, None, 0] for metric in self.supported_metric_names]
            ).reset_index()
        else:
            element_metrics_results = {}
            for metric in self.supported_metric_names:
                metric_df = has_tables_df[has_tables_df[metric].notnull()]
                agg_metric = metric_df[metric].agg([_stdev, _pstdev, _count]).transpose()
                if metric.startswith("total_tables"):
                    agg_metric["_mean"] = metric_df[metric].mean()
                elif metric.startswith("table_level_acc"):
                    agg_metric["_mean"] = np.round(
                        np.average(metric_df[metric], weights=metric_df["_table_weights"]),
                        3,
                    )
                else:
                    # false positive tables do not contribute to table structure and content
                    # extraction metrics
                    agg_metric["_mean"] = np.round(
                        np.average(metric_df[metric], weights=metric_df["total_tables"]),
                        3,
                    )
                if agg_metric.empty:
                    element_metrics_results[metric] = pd.Series(
                        data=[None, None, None, 0], index=["_mean", "_stdev", "_pstdev", "_count"]
                    )
                else:
                    element_metrics_results[metric] = agg_metric
            agg_df = pd.DataFrame(element_metrics_results).transpose().reset_index()
        agg_df = agg_df.rename(columns=AGG_HEADERS_MAPPING)
        return df, agg_df


@dataclass
class TextExtractionMetricsCalculator(BaseMetricsCalculator):
    """Calculates text accuracy and percent missing between document and ground truth texts.

    It also calculates the aggregated accuracy and percent missing.
    """

    group_by: Optional[str] = None
    weights: tuple[int, int, int] = (1, 1, 1)
    document_type: str = "json"

    def __post_init__(self):
        super().__post_init__()
        self._validate_inputs()

    @property
    def default_tsv_name(self) -> str:
        return "all-docs-cct.tsv"

    @property
    def default_agg_tsv_name(self) -> str:
        return "aggregate-scores-cct.tsv"

    def calculate(
        self,
        executor: Optional[concurrent.futures.Executor] = None,
        export_dir: Optional[str | Path] = None,
        visualize_progress: bool = True,
        display_agg_df: bool = True,
    ) -> pd.DataFrame:
        """See the parent class for the method's docstring."""
        df = super().calculate(
            executor=executor,
            export_dir=export_dir,
            visualize_progress=visualize_progress,
            display_agg_df=display_agg_df,
        )

        if export_dir is not None and self.group_by:
            get_mean_grouping(self.group_by, df, export_dir, "text_extraction")
        return df

    def _validate_inputs(self):
        if not self._document_paths:
            logger.info("No output files to calculate to edit distances for, exiting")
            sys.exit(0)
        if self.document_type not in OUTPUT_TYPE_OPTIONS:
            raise ValueError(
                "Specified file type under `documents_dir` or `output_list` should be one of "
                f"`json` or `txt`. The given file type is {self.document_type}, exiting."
            )
        for path in self._document_paths:
            try:
                path.suffixes[-1]
            except IndexError:
                logger.error(f"File {path} does not have a suffix, skipping")
                continue
            if path.suffixes[-1] != f".{self.document_type}":
                logger.warning(
                    "The directory contains file type inconsistent with the given input. "
                    "Please note that some files will be skipped."
                )
        if not all(path.suffixes[-1] == f".{self.document_type}" for path in self._document_paths):
            logger.warning(
                "The directory contains file type inconsistent with the given input. "
                "Please note that some files will be skipped."
            )

    def _process_document(self, doc: Path) -> Optional[list]:
        filename = doc.stem
        doctype = doc.suffixes[0]
        connector = doc.parts[0] if len(doc.parts) > 1 else None

        output_cct, source_cct = self._get_ccts(doc)
        # NOTE(amadeusz): Levenshtein distance calculation takes too long
        # skip it if file sizes differ wildly
        if 0.5 < len(output_cct.encode()) / len(source_cct.encode()) < 2.0:
            accuracy = round(calculate_accuracy(output_cct, source_cct, self.weights), 3)
        else:
            # 0.01 to distinguish it was set manually
            accuracy = 0.01
        percent_missing = round(calculate_percent_missing_text(output_cct, source_cct), 3)
        return [filename, doctype, connector, accuracy, percent_missing]

    def _get_ccts(self, doc: Path) -> tuple[str, str]:
        output_cct = _prepare_output_cct(
            docpath=self.documents_dir / doc, output_type=self.document_type
        )
        source_cct = _read_text_file(self.ground_truths_dir / doc.with_suffix(".txt"))

        return output_cct, source_cct

    def _generate_dataframes(self, rows):
        headers = ["filename", "doctype", "connector", "cct-accuracy", "cct-%missing"]
        df = pd.DataFrame(rows, columns=headers)

        acc = df[["cct-accuracy"]].agg([_mean, _stdev, _pstdev, _count]).transpose()
        miss = df[["cct-%missing"]].agg([_mean, _stdev, _pstdev, _count]).transpose()
        if acc.shape[1] == 0 and miss.shape[1] == 0:
            agg_df = pd.DataFrame(columns=AGG_HEADERS)
        else:
            agg_df = pd.concat((acc, miss)).reset_index()
            agg_df.columns = AGG_HEADERS

        return df, agg_df


@dataclass
class ElementTypeMetricsCalculator(BaseMetricsCalculator):
    """
    Calculates element type frequency accuracy, percent missing and
    aggregated accuracy between document and ground truth.
    """

    group_by: Optional[str] = None

    def calculate(
        self,
        executor: Optional[concurrent.futures.Executor] = None,
        export_dir: Optional[str | Path] = None,
        visualize_progress: bool = True,
        display_agg_df: bool = False,
    ) -> pd.DataFrame:
        """See the parent class for the method's docstring."""
        df = super().calculate(
            executor=executor,
            export_dir=export_dir,
            visualize_progress=visualize_progress,
            display_agg_df=display_agg_df,
        )

        if export_dir is not None and self.group_by:
            get_mean_grouping(self.group_by, df, export_dir, "element_type")
        return df

    @property
    def default_tsv_name(self) -> str:
        return "all-docs-element-type-frequency.tsv"

    @property
    def default_agg_tsv_name(self) -> str:
        return "aggregate-scores-element-type.tsv"

    def _process_document(self, doc: Path) -> Optional[list]:
        filename = doc.stem
        doctype = doc.suffixes[0]
        connector = doc.parts[0] if len(doc.parts) > 1 else None

        output = get_element_type_frequency(_read_text_file(self.documents_dir / doc))
        source = get_element_type_frequency(
            _read_text_file(self.ground_truths_dir / doc.with_suffix(".json"))
        )
        accuracy = round(calculate_element_type_percent_match(output, source), 3)
        return [filename, doctype, connector, accuracy]

    def _generate_dataframes(self, rows):
        headers = ["filename", "doctype", "connector", "element-type-accuracy"]
        df = pd.DataFrame(rows, columns=headers)
        if df.empty:
            agg_df = pd.DataFrame(["element-type-accuracy", None, None, None, 0]).transpose()
        else:
            agg_df = df.agg({"element-type-accuracy": [_mean, _stdev, _pstdev, _count]}).transpose()
            agg_df = agg_df.reset_index()

        agg_df.columns = AGG_HEADERS

        return df, agg_df


def get_mean_grouping(
    group_by: str,
    data_input: Union[pd.DataFrame, str],
    export_dir: str,
    eval_name: str,
    agg_name: Optional[str] = None,
    export_filename: Optional[str] = None,
) -> None:
    """Aggregates accuracy and missing metrics by column name 'doctype' or 'connector',
    or 'all' for all rows. Export to TSV.
    If `all`, passing export_name is recommended.

    Args:
        group_by (str): Grouping category ('doctype' or 'connector' or 'all').
        data_input (Union[pd.DataFrame, str]): DataFrame or path to a CSV/TSV file.
        export_dir (str): Directory for the exported TSV file.
        eval_name (str): Evaluated metric ('text_extraction' or 'element_type').
        agg_name (str, optional): String to use with export filename. Default is `cct` for
            group_by `text_extraction` and `element-type` for `element_type`
        export_name (str, optional): Export filename.
    """
    if group_by not in ("doctype", "connector") and group_by != "all":
        raise ValueError("Invalid grouping category. Returning a non-group evaluation.")

    if eval_name == "text_extraction":
        agg_fields = ["cct-accuracy", "cct-%missing"]
        agg_name = "cct"
    elif eval_name == "element_type":
        agg_fields = ["element-type-accuracy"]
        agg_name = "element-type"
    elif eval_name == "object_detection":
        agg_fields = ["f1_score", "m_ap"]
        agg_name = "object-detection"
    else:
        raise ValueError(
            f"Unknown metric for eval {eval_name}. "
            f"Expected `text_extraction` or `element_type` or `table_extraction`."
        )

    if isinstance(data_input, str):
        if not os.path.exists(data_input):
            raise FileNotFoundError(f"File {data_input} not found.")
        if data_input.endswith(".csv"):
            df = pd.read_csv(data_input, header=None)
        elif data_input.endswith(".tsv"):
            df = pd.read_csv(data_input, sep="\t")
        elif data_input.endswith(".txt"):
            df = pd.read_csv(data_input, sep="\t", header=None)
        else:
            raise ValueError("Please provide a .csv or .tsv file.")
    else:
        df = data_input

    if df.empty:
        raise SystemExit("Data is empty. Exiting.")
    elif group_by != "all" and (group_by not in df.columns or df[group_by].isnull().all()):
        raise SystemExit(
            f"Data cannot be aggregated by `{group_by}`."
            f" Check if it's empty or the column is missing/empty."
        )

    grouped_df = []
    if group_by and group_by != "all":
        for field in agg_fields:
            grouped_df.append(
                _rename_aggregated_columns(
                    df.groupby(group_by).agg({field: [_mean, _stdev, _pstdev, _count]})
                )
            )
    if group_by == "all":
        df["grouping_key"] = 0
        for field in agg_fields:
            grouped_df.append(
                _rename_aggregated_columns(
                    df.groupby("grouping_key").agg({field: [_mean, _stdev, _pstdev, _count]})
                )
            )
    grouped_df = _format_grouping_output(*grouped_df)
    if "grouping_key" in grouped_df.columns.get_level_values(0):
        grouped_df = grouped_df.drop("grouping_key", axis=1, level=0)

    if export_filename:
        if not export_filename.endswith(".tsv"):
            export_filename = export_filename + ".tsv"
        _write_to_file(export_dir, export_filename, grouped_df)
    else:
        _write_to_file(export_dir, f"all-{group_by}-agg-{agg_name}.tsv", grouped_df)


def filter_metrics(
    data_input: Union[str, pd.DataFrame],
    filter_list: Union[str, List[str]],
    filter_by: str = "filename",
    export_filename: Optional[str] = None,
    export_dir: str = "metrics",
    return_type: str = "file",
) -> Optional[pd.DataFrame]:
    """Reads the data_input file and filter only selected row available in filter_list.

    Args:
        data_input (str, dataframe): the source data, path to file or dataframe
        filter_list (str, list): the filter, path to file or list of string
        filter_by (str): data_input's column to filter the filter_list to
        export_filename (str, optional): export filename. required when return_type is "file"
        export_dir (str, optional): export directory. default to <current directory>/metrics
        return_type (str): "file" or "dataframe"
    """
    if isinstance(data_input, str):
        if not os.path.exists(data_input):
            raise FileNotFoundError(f"File {data_input} not found.")
        if data_input.endswith(".csv"):
            df = pd.read_csv(data_input, header=None)
        elif data_input.endswith(".tsv"):
            df = pd.read_csv(data_input, sep="\t")
        elif data_input.endswith(".txt"):
            df = pd.read_csv(data_input, sep="\t", header=None)
        else:
            raise ValueError("Please provide a .csv or .tsv file.")
    else:
        df = data_input

    if isinstance(filter_list, str):
        if not os.path.exists(filter_list):
            raise FileNotFoundError(f"File {filter_list} not found.")
        if filter_list.endswith(".csv"):
            filter_df = pd.read_csv(filter_list, header=None)
        elif filter_list.endswith(".tsv"):
            filter_df = pd.read_csv(filter_list, sep="\t")
        elif filter_list.endswith(".txt"):
            filter_df = pd.read_csv(filter_list, sep="\t", header=None)
        else:
            raise ValueError("Please provide a .csv or .tsv file.")
        filter_list = filter_df.iloc[:, 0].astype(str).values.tolist()
    elif not isinstance(filter_list, list):
        raise ValueError("Please provide a List of strings or path to file.")

    if filter_by not in df.columns:
        raise ValueError("`filter_by` key does not exists in the data provided.")

    res = df[df[filter_by].isin(filter_list)]

    if res.empty:
        raise SystemExit("No common file names between data_input and filter_list. Exiting.")

    if return_type == "dataframe":
        return res
    elif return_type == "file" and export_filename:
        _write_to_file(export_dir, export_filename, res)
    elif return_type == "file" and not export_filename:
        raise ValueError("Please provide `export_filename`.")
    else:
        raise ValueError("Return type must be either `dataframe` or `file`.")


@dataclass
class ObjectDetectionMetricsCalculatorBase(BaseMetricsCalculator, ABC):
    """
    Calculates object detection metrics for each document:
    - f1 score
    - precision
    - recall
    - average precision (mAP)
    It also calculates aggregated metrics.
    """

    def __post_init__(self):
        super().__post_init__()
        self._document_paths = [
            path.relative_to(self.documents_dir)
            for path in self.documents_dir.rglob("analysis/*/layout_dump/object_detection.json")
            if path.is_file()
        ]

    @property
    def supported_metric_names(self):
        return ["f1_score", "precision", "recall", "m_ap"]

    @property
    def default_tsv_name(self):
        return "all-docs-object-detection-metrics.tsv"

    @property
    def default_agg_tsv_name(self):
        return "aggregate-object-detection-metrics.tsv"

    def _find_file_in_ground_truth(self, file_stem: str) -> Optional[Path]:
        """Find the file corresponding to OD model dump file among the set of ground truth files

        The files in ground truth paths keep the original extension and have .json suffix added,
        e.g.:
        some_document.pdf.json
        poster.jpg.json

        To compare to `file_stem` we need to take the prefix part of the file, thus double-stem
        is applied.
        """
        for path in self._ground_truth_paths:
            if Path(path.stem).stem == file_stem:
                return path
        return None

    def _get_paths(self, doc: Path) -> tuple(str, Path, Path):
        """Resolves ground doctype, prediction file path and ground truth path.

        As OD dump directory structure differes from other simple outputs, it needs
        a specific processing to match the output OD dump file with corresponding
        OD GT file.

        The outputs are placed in a dicrectory structure:

        analysis
        |- document_name
            |- layout_dump
                |- object_detection.json
            |- bboxes # not used in this evaluation

        and the GT file is pleced in od_gt directory for given dataset

        dataset_name
        |- od_gt
            |- document_name.pdf.json

        Args:
            doc (Path): path to the OD dump file

        Returns:
            tuple: doctype, prediction file path, ground truth path
        """
        od_dump_path = Path(doc)
        file_stem = od_dump_path.parts[-3]  # we take the `document_name` - so the filename stem

        src_gt_filename = self._find_file_in_ground_truth(file_stem)

        if src_gt_filename not in self._ground_truth_paths:
            raise ValueError(f"Ground truth file {src_gt_filename} not found in list of GT files")

        doctype = Path(src_gt_filename.stem).suffix[1:]

        prediction_file = self.documents_dir / doc
        if not prediction_file.exists():
            logger.warning(f"Prediction file {prediction_file} does not exist, skipping")
            raise ValueError(f"Prediction file {prediction_file} does not exist")

        ground_truth_file = self.ground_truths_dir / src_gt_filename
        if not ground_truth_file.exists():
            logger.warning(f"Ground truth file {ground_truth_file} does not exist, skipping")
            raise ValueError(f"Ground truth file {ground_truth_file} does not exist")

        return doctype, prediction_file, ground_truth_file

    def _generate_dataframes(self, rows) -> tuple[pd.DataFrame, pd.DataFrame]:
        headers = ["filename", "doctype", "connector"] + self.supported_metric_names
        df = pd.DataFrame(rows, columns=headers)

        if df.empty:
            agg_df = pd.DataFrame(columns=AGG_HEADERS)
        else:
            element_metrics_results = {}
            for metric in self.supported_metric_names:
                metric_df = df[df[metric].notnull()]
                agg_metric = metric_df[metric].agg([_mean, _stdev, _pstdev, _count]).transpose()
                if agg_metric.empty:
                    element_metrics_results[metric] = pd.Series(
                        data=[None, None, None, 0], index=["_mean", "_stdev", "_pstdev", "_count"]
                    )
                else:
                    element_metrics_results[metric] = agg_metric
            agg_df = pd.DataFrame(element_metrics_results).transpose().reset_index()
        agg_df.columns = AGG_HEADERS

        return df, agg_df


class ObjectDetectionPerClassMetricsCalculator(ObjectDetectionMetricsCalculatorBase):

    def __post_init__(self):
        super().__post_init__()
        self.per_class_metric_names: list[str] | None = None
        self._set_supported_metrics()

    @property
    def supported_metric_names(self):
        if self.per_class_metric_names:
            return self.per_class_metric_names
        else:
            raise ValueError("per_class_metrics not initialized - cannot get class names")

    @property
    def default_tsv_name(self):
        return "all-docs-object-detection-metrics-per-class.tsv"

    @property
    def default_agg_tsv_name(self):
        return "aggregate-object-detection-metrics-per-class.tsv"

    def _process_document(self, doc: Path) -> Optional[list]:
        """Calculate both class-aggregated and per-class metrics for a single document.

        Args:
            doc (Path): path to the OD dump file

        Returns:
            tuple: a tuple of aggregated and per-class metrics for a single document
        """
        try:
            doctype, prediction_file, ground_truth_file = self._get_paths(doc)
        except ValueError as e:
            logger.error(f"Failed to process document {doc}: {e}")
            return None

        processor = ObjectDetectionEvalProcessor.from_json_files(
            prediction_file_path=prediction_file,
            ground_truth_file_path=ground_truth_file,
        )
        _, per_class_metrics = processor.get_metrics()

        per_class_metrics_row = [
            ground_truth_file.stem,
            doctype,
            None,  # connector
        ]

        for combined_metric_name in self.supported_metric_names:
            metric = "_".join(combined_metric_name.split("_")[:-1])
            class_name = combined_metric_name.split("_")[-1]
            class_metrics = getattr(per_class_metrics, metric)
            per_class_metrics_row.append(class_metrics[class_name])
        return per_class_metrics_row

    def _set_supported_metrics(self):
        """Sets the supported metrics based on the classes found in the ground truth files.
        The difference between per class and aggregated calculator is that the list of classes
        (so the metrics) bases on the contents of the GT / prediction files.
        """
        metrics = ["f1_score", "precision", "recall", "m_ap"]
        classes = set()
        for gt_file in self._ground_truth_paths:
            gt_file_path = self.ground_truths_dir / gt_file
            with open(gt_file_path) as f:
                gt = json.load(f)
                gt_classes = gt["object_detection_classes"]
                classes.update(gt_classes)
        per_class_metric_names = []
        for metric in metrics:
            for class_name in classes:
                per_class_metric_names.append(f"{metric}_{class_name}")
        self.per_class_metric_names = sorted(per_class_metric_names)


class ObjectDetectionAggregatedMetricsCalculator(ObjectDetectionMetricsCalculatorBase):
    """Calculates object detection metrics for each document and aggregates by all classes"""

    @property
    def supported_metric_names(self):
        return ["f1_score", "precision", "recall", "m_ap"]

    @property
    def default_tsv_name(self):
        return "all-docs-object-detection-metrics.tsv"

    @property
    def default_agg_tsv_name(self):
        return "aggregate-object-detection-metrics.tsv"

    def _process_document(self, doc: Path) -> Optional[list]:
        """Calculate both class-aggregated and per-class metrics for a single document.

        Args:
            doc (Path): path to the OD dump file

        Returns:
            list: a list of aggregated metrics for a single document
        """
        try:
            doctype, prediction_file, ground_truth_file = self._get_paths(doc)
        except ValueError as e:
            logger.error(f"Failed to process document {doc}: {e}")
            return None

        processor = ObjectDetectionEvalProcessor.from_json_files(
            prediction_file_path=prediction_file,
            ground_truth_file_path=ground_truth_file,
        )
        metrics, _ = processor.get_metrics()

        return [
            ground_truth_file.stem,
            doctype,
            None,  # connector
        ] + [getattr(metrics, metric) for metric in self.supported_metric_names]
