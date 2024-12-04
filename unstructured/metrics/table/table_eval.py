"""
The purpose of this script is to create a comprehensive metric for table evaluation
1. Verify table identification.
    a. Concatenate all text in the table and ground truth.
    b. Calculate the difference to find the closest matches.
    c. If contents are too different, mark as a failure.

2. For each identified table:
    a. Align elements at the level of individual elements.
    b. Match elements by text.
    c. Determine indexes for both predicted and actual data.
    d. Compare index tuples at column and row levels to assess content shifts.
    e. Compare the token orders by flattened along column and row levels
    f. Note: Imperfect HTML is acceptable unless it impedes parsing,
       in which case the table is considered failed.

Example
python table_eval.py  \
    --prediction_file "model_output.pdf.json" \
    --ground_truth_file "ground_truth.pdf.json"
"""

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import numpy as np

from unstructured.metrics.table.table_alignment import TableAlignment
from unstructured.metrics.table.table_extraction import (
    extract_and_convert_tables_from_ground_truth,
    extract_and_convert_tables_from_prediction,
)


@dataclass
class TableEvaluation:
    """Class representing a gathered table metrics."""

    total_tables: int
    total_predicted_tables: int
    table_level_acc: float
    table_detection_recall: float
    table_detection_precision: float
    table_detection_f1: float
    element_col_level_index_acc: float
    element_row_level_index_acc: float
    element_col_level_content_acc: float
    element_row_level_content_acc: float

    @property
    def composite_structure_acc(self) -> float:
        return (
            self.element_col_level_index_acc
            + self.element_row_level_index_acc
            + (self.element_col_level_content_acc + self.element_row_level_content_acc) / 2
        ) / 3


def table_level_acc(predicted_table_data, ground_truth_table_data, matched_indices):
    """computes for each predicted table its accurary compared to ground truth.

    The accuracy is defined as the SequenceMatcher.ratio() between those two strings. If a
    prediction does not have a matched ground truth its accuracy is 0
    """
    score = np.zeros((len(matched_indices),))
    ground_truth_text = TableAlignment.get_content_in_tables(ground_truth_table_data)
    for idx, predicted in enumerate(predicted_table_data):
        matched_idx = matched_indices[idx]
        if matched_idx == -1:
            # false positive; default score 0
            continue
        score[idx] = difflib.SequenceMatcher(
            None,
            TableAlignment.get_content_in_tables([predicted])[0],
            ground_truth_text[matched_idx],
        ).ratio()
    return score


def _count_predicted_tables(matched_indices: List[int]) -> int:
    """Counts the number of predicted tables that have a corresponding match in the ground truth.

    Args:
      matched_indices: List of indices indicating matches between predicted
        and ground truth tables.

    Returns:
      The count of matched predicted tables.

    """
    return sum(1 for idx in matched_indices if idx >= 0)


def calculate_table_detection_metrics(
    matched_indices: list[int], ground_truth_tables_number: int
) -> tuple[float, float, float]:
    """
    Calculate the table detection metrics: recall, precision, and f1 score.
    Args:
        matched_indices:
            List of indices indicating matches between predicted and ground truth tables
            For example: matched_indices[i] = j means that the
            i-th predicted table is matched with the j-th ground truth table.
        ground_truth_tables_number: the number of ground truth tables.

    Returns:
        Tuple of recall, precision, and f1 scores
    """
    predicted_tables_number = len(matched_indices)

    matched_set = set(matched_indices)
    if -1 in matched_set:
        matched_set.remove(-1)

    true_positive = len(matched_set)
    false_positive = predicted_tables_number - true_positive
    positive = ground_truth_tables_number

    recall = true_positive / positive if positive > 0 else 0
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive > 0
        else 0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0

    return recall, precision, f1


class TableEvalProcessor:
    def __init__(
        self,
        prediction: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
        cutoff: float = 0.8,
        source_type: str = "html",
    ):
        """
        Initializes the TableEvalProcessor prediction and ground truth.

        Args:
            ground_truth: Ground truth table data. The tables text should be in the deckerd format.
            prediction: Predicted table data.
            cutoff: The cutoff value for the element level alignment. Default is 0.8.

        Examples:
            ground_truth: [
                {
                    "type": "Table",
                    "text": [
                        {
                            "id": "f4c35dae-105b-46f5-a77a-7fbc199d6aca",
                            "x": 0,
                            "y": 0,
                            "w": 1,
                            "h": 1,
                            "content": "Cell text"
                        },
                        ...
                }
            ]
            prediction: [
                {
                    "element_id": <id_string>,
                    ...
                    "metadata": {
                        ...
                        "text_as_html": "<table><thead><tr><th rowspan=\"2\">June....
                                                                </tr></td></table>",
                        "table_as_cells":
                        [
                            {
                                "x": 0,
                                "y": 0,
                                "w": 1,
                                "h": 2,
                                "content": "June"
                            },
                            ...
                        ]
                    }
                },
            ]

        """
        self.prediction = prediction
        self.ground_truth = ground_truth
        self.cutoff = cutoff
        self.source_type = source_type

    @classmethod
    def from_json_files(
        cls,
        prediction_file: Path,
        ground_truth_file: Path,
        cutoff: Optional[float] = None,
        source_type: str = "html",
    ) -> "TableEvalProcessor":
        """Factory classmethod to initialize the object with path to json files instead of dicts

        Args:
          prediction_file: Path to the json file containing the predicted table data.
          ground_truth_file: Path to the json file containing the ground truth table data.
          source_type: 'cells' or 'html'. 'cells' refers to reading 'table_as_cells' field while
            'html' is extracted from 'text_as_html'
          cutoff: The cutoff value for the element level alignment.
            If not set, class default value is used (=0.8).

        Returns:
          TableEvalProcessor: An instance of the class initialized with the provided data.
        """
        with open(prediction_file) as f:
            prediction = json.load(f)
        with open(ground_truth_file) as f:
            ground_truth = json.load(f)
        if cutoff is not None:
            return cls(
                prediction=prediction,
                ground_truth=ground_truth,
                cutoff=cutoff,
                source_type=source_type,
            )
        else:
            return cls(prediction=prediction, ground_truth=ground_truth, source_type=source_type)

    def process_file(self) -> TableEvaluation:
        """Processes the files and computes table-level and element-level accuracy.

        Returns:
            TableEvaluation: A dataclass object containing the computed metrics.
        """
        ground_truth_table_data = extract_and_convert_tables_from_ground_truth(
            self.ground_truth,
        )

        predicted_table_data = extract_and_convert_tables_from_prediction(
            file_elements=self.prediction, source_type=self.source_type
        )
        is_table_in_gt = bool(ground_truth_table_data)
        is_table_predicted = bool(predicted_table_data)
        if not is_table_in_gt:
            # There is no table data in ground truth, you either got perfect score or 0
            score = 0 if is_table_predicted else np.nan
            table_acc = 1 if not is_table_predicted else 0
            return TableEvaluation(
                total_tables=0,
                total_predicted_tables=len(predicted_table_data),
                table_level_acc=table_acc,
                table_detection_recall=score,
                table_detection_precision=score,
                table_detection_f1=score,
                element_col_level_index_acc=score,
                element_row_level_index_acc=score,
                element_col_level_content_acc=score,
                element_row_level_content_acc=score,
            )
        if is_table_in_gt and not is_table_predicted:
            return TableEvaluation(
                total_tables=len(ground_truth_table_data),
                total_predicted_tables=0,
                table_level_acc=0,
                table_detection_recall=0,
                table_detection_precision=0,
                table_detection_f1=0,
                element_col_level_index_acc=0,
                element_row_level_index_acc=0,
                element_col_level_content_acc=0,
                element_row_level_content_acc=0,
            )
        else:
            # We have both ground truth tables and predicted tables
            matched_indices = TableAlignment.get_table_level_alignment(
                predicted_table_data,
                ground_truth_table_data,
            )
            predicted_table_acc = np.mean(
                table_level_acc(predicted_table_data, ground_truth_table_data, matched_indices)
            )

            metrics = TableAlignment.get_element_level_alignment(
                predicted_table_data,
                ground_truth_table_data,
                matched_indices,
                cutoff=self.cutoff,
            )

            table_detection_recall, table_detection_precision, table_detection_f1 = (
                calculate_table_detection_metrics(
                    matched_indices=matched_indices,
                    ground_truth_tables_number=len(ground_truth_table_data),
                )
            )

            evaluation = TableEvaluation(
                total_tables=len(ground_truth_table_data),
                total_predicted_tables=len(predicted_table_data),
                table_level_acc=predicted_table_acc,
                table_detection_recall=table_detection_recall,
                table_detection_precision=table_detection_precision,
                table_detection_f1=table_detection_f1,
                element_col_level_index_acc=metrics.get("col_index_acc", 0),
                element_row_level_index_acc=metrics.get("row_index_acc", 0),
                element_col_level_content_acc=metrics.get("col_content_acc", 0),
                element_row_level_content_acc=metrics.get("row_content_acc", 0),
            )
            return evaluation


@click.command()
@click.option(
    "--prediction_file", help="Path to the model prediction JSON file", type=click.Path(exists=True)
)
@click.option(
    "--ground_truth_file", help="Path to the ground truth JSON file", type=click.Path(exists=True)
)
@click.option(
    "--cutoff",
    type=float,
    show_default=True,
    default=0.8,
    help="The cutoff value for the element level alignment. \
        If not set, a default value is used",
)
def run(prediction_file: str, ground_truth_file: str, cutoff: Optional[float]):
    """Runs the table evaluation process and prints the computed metrics."""
    processor = TableEvalProcessor.from_json_files(
        Path(prediction_file),
        Path(ground_truth_file),
        cutoff=cutoff,
    )
    report = processor.process_file()
    print(report)


if __name__ == "__main__":
    run()
