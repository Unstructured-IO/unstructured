from copy import deepcopy

import pytest

from unstructured.metrics.table.table_alignment import TableAlignment
from unstructured.metrics.table.table_eval import TableEvalProcessor


def _table(text):
    return [{"row_index": 0, "col_index": 0, "content": text}]


@pytest.mark.parametrize(
    ("predicted", "ground_truth", "expected"),
    [
        (["Balance", "Balance"], ["Balance", "Balance"], [0, 1]),
        (["Balance", "Total", "Balance"], ["Balance", "Total", "Balance"], [0, 1, 2]),
        (["Balance", "Balance", "Balance"], ["Balance", "Balance"], [0, 1, 0]),
        (["Balance", "Balance"], ["Balance"], [0, 0]),
        (["Balanc", "Balanc"], ["Balance", "Balance"], [0, 1]),
        (["Total", "Balance"], ["Balance", "Total"], [1, 0]),
        (["ZZZZ"], ["aaaa", "aaaa"], [-1]),
        ([], ["Balance", "Balance"], []),
    ],
)
def test_repeated_table_occurrences_are_aligned_independently(predicted, ground_truth, expected):
    predicted_tables = [_table(text) for text in predicted]
    ground_truth_tables = [_table(text) for text in ground_truth]
    original = deepcopy((predicted_tables, ground_truth_tables))

    assert (
        TableAlignment.get_table_level_alignment(predicted_tables, ground_truth_tables) == expected
    )
    assert (predicted_tables, ground_truth_tables) == original


@pytest.mark.parametrize(
    ("predicted_count", "ground_truth_count", "recall", "precision"),
    [(2, 2, 1.0, 1.0), (3, 2, 1.0, 2 / 3), (2, 3, 2 / 3, 1.0)],
)
def test_repeated_tables_contribute_separately_to_document_detection_metrics(
    predicted_count, ground_truth_count, recall, precision
):
    cells = [{"x": 0, "y": 0, "w": 1, "h": 1, "content": "Balance 100"}]
    prediction = [
        {"type": "Table", "metadata": {"table_as_cells": deepcopy(cells)}}
        for _ in range(predicted_count)
    ]
    ground_truth = [{"type": "Table", "text": deepcopy(cells)} for _ in range(ground_truth_count)]

    result = TableEvalProcessor(prediction, ground_truth, source_type="cells").process_file()

    assert result.total_predicted_tables == predicted_count
    assert result.total_tables == ground_truth_count
    assert result.table_detection_recall == pytest.approx(recall)
    assert result.table_detection_precision == pytest.approx(precision)
    assert result.table_detection_f1 == pytest.approx(2 * recall * precision / (recall + precision))
    if predicted_count == ground_truth_count:
        assert result.composite_structure_acc == 1.0
