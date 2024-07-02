import pytest

from unstructured.metrics.table.table_eval import calculate_table_detection_metrics


@pytest.mark.parametrize(
    ("matched_indices", "ground_truth_tables_number", "expected_metrics"),
    [
        ([0, 1, 2], 3, (1, 1, 1)),  # everything was predicted correctly
        ([2, 1, 0], 3, (1, 1, 1)),  # everything was predicted correctly
        (
            [-1, 2, -1, 1, 0, -1],
            3,
            (1, 0.5, 0.66),
        ),  # some false positives, all tables matched, too many predictions
        ([2, 2, 1, 1], 8, (0.25, 0.5, 0.33)),
        # Some false negatives, all predictions matched with gt, not enough predictions
        # The precision here is not 1 as only one from tables matched with '1' index can be correct
        ([1, -1], 2, (0.5, 0.5, 0.5)),  # typical case with false positive and false negative
        ([-1, -1, -1], 2, (0, 0, 0)),  # nothing was matched
        ([-1, -1, -1], 0, (0, 0, 0)),  # there was no table in ground truth
        ([], 0, (0, 0, 0)),  # just zeros to account for errors
    ],
)
def test_calculate_table_metrics(matched_indices, ground_truth_tables_number, expected_metrics):
    expected_recall, expected_precision, expected_f1 = expected_metrics
    pred_recall, pred_precision, pred_f1 = calculate_table_detection_metrics(
        matched_indices=matched_indices, ground_truth_tables_number=ground_truth_tables_number
    )

    assert pred_recall == expected_recall
    assert pred_precision == expected_precision
    assert pred_f1 == pytest.approx(expected_f1, abs=0.01)
