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
    table_level_acc: float
    element_col_level_index_acc: float
    element_row_level_index_acc: float
    element_col_level_content_acc: float
    element_row_level_content_acc: float


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


class TableEvalProcessor:
    def __init__(
        self,
        prediction: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
        cutoff: float = 0.8,
    ):
        """
        Initializes the TableEvalProcessor prediction and ground truth.

        Args:
            prediction: Predicted table data.
            ground_truth: Ground truth table data. The tables text should be in the deckerd format.
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
                        "text_as_html": "<table><thead><th rowspan=\"2\">June....</tr></td></table>"
                    },
                }
            ]

        """
        self.prediction = prediction
        self.ground_truth = ground_truth
        self.cutoff = cutoff

    @classmethod
    def from_json_files(
        cls,
        prediction_file: Path,
        ground_truth_file: Path,
        cutoff: Optional[float] = None,
    ) -> "TableEvalProcessor":
        """Factory classmethod to initialize the object with path to json files instead of dicts

        Args:
          prediction_file: Path to the json file containing the predicted table data.
          ground_truth_file: Path to the json file containing the ground truth table data.
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
            return cls(prediction=prediction, ground_truth=ground_truth, cutoff=cutoff)
        else:
            return cls(prediction=prediction, ground_truth=ground_truth)

    def process_file(self) -> TableEvaluation:
        """Processes the files and computes table-level and element-level accuracy.

        Returns:
            TableEvaluation: A dataclass object containing the computed metrics.
        """

        predicted_table_data = extract_and_convert_tables_from_prediction(
            self.prediction,
        )
        ground_truth_table_data = extract_and_convert_tables_from_ground_truth(
            self.ground_truth,
        )

        matched_indices = TableAlignment.get_table_level_alignment(
            predicted_table_data,
            ground_truth_table_data,
        )
        if matched_indices:
            predicted_table_acc = np.mean(
                table_level_acc(predicted_table_data, ground_truth_table_data, matched_indices)
            )
        elif ground_truth_table_data:
            # no matching prediction but has actual table -> total failure
            predicted_table_acc = 0
        else:
            # no predicted and no actual table -> good job
            predicted_table_acc = 1

        metrics = TableAlignment.get_element_level_alignment(
            predicted_table_data,
            ground_truth_table_data,
            matched_indices,
            cutoff=self.cutoff,
        )

        return TableEvaluation(
            total_tables=len(ground_truth_table_data),
            table_level_acc=predicted_table_acc,
            element_col_level_index_acc=metrics.get("col_index_acc", np.nan),
            element_row_level_index_acc=metrics.get("row_index_acc", np.nan),
            element_col_level_content_acc=metrics.get("col_content_acc", np.nan),
            element_row_level_content_acc=metrics.get("row_content_acc", np.nan),
        )


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
