"""Fixed-score detection precision is computed from the accepted detections."""

import pytest
import torch

from unstructured.metrics.object_detection import ObjectDetectionEvalProcessor


@pytest.mark.parametrize("order", [(0, 1, 2), (2, 0, 1)])
@pytest.mark.parametrize(
    ("threshold", "precision", "recall", "f1"),
    [
        (0.0, 2 / 3, 1, 4 / 5),
        (0.05, 2 / 3, 1, 4 / 5),
        (0.1, 1 / 2, 1 / 2, 1 / 2),
        (0.8, 1 / 2, 1 / 2, 1 / 2),
        (0.85, 0, 0, 0),
        (1.0, 0, 0, 0),
    ],
)
def test_score_threshold_uses_actual_counts_without_the_ap_envelope(
    order, threshold, precision, recall, f1
):
    predictions = torch.tensor(
        [[70, 70, 80, 80, 0.9, 0], [10, 10, 20, 20, 0.8, 0], [30, 30, 40, 40, 0.05, 0]],
        dtype=torch.float64,
    )[list(order)]
    targets = torch.tensor([[0, 10, 10, 20, 20], [0, 30, 30, 40, 40]])
    processor = ObjectDetectionEvalProcessor([predictions], [targets], [100], [100], ["Text"])
    processor.score_threshold = threshold

    aggregate, per_class = processor.get_metrics()

    assert aggregate.precision == pytest.approx(precision)
    assert aggregate.recall == pytest.approx(recall)
    assert aggregate.f1_score == pytest.approx(f1)
    # The interpolated AP envelope remains 2/3 at every recall sample,
    # independently of the threshold used for the other three metrics.
    assert aggregate.m_ap == pytest.approx(2 / 3)
    assert per_class.precision == pytest.approx({"Text": precision})
    assert per_class.recall == pytest.approx({"Text": recall})
    assert per_class.f1_score == pytest.approx({"Text": f1})
    assert per_class.m_ap == pytest.approx({"Text": 2 / 3})


def test_macro_metrics_average_the_uninterpolated_precision_for_each_class():
    predictions = torch.tensor(
        [
            [70, 70, 80, 80, 0.9, 0],
            [10, 10, 20, 20, 0.8, 0],
            [30, 30, 40, 40, 0.05, 0],
            [50, 50, 60, 60, 0.95, 1],
        ]
    )
    targets = torch.tensor([[0, 10, 10, 20, 20], [0, 30, 30, 40, 40], [1, 50, 50, 60, 60]])
    processor = ObjectDetectionEvalProcessor(
        [predictions], [targets], [100], [100], ["Text", "Title"]
    )

    aggregate, per_class = processor.get_metrics()

    assert aggregate.precision == pytest.approx(3 / 4)
    assert aggregate.recall == pytest.approx(3 / 4)
    assert aggregate.f1_score == pytest.approx(3 / 4)
    assert aggregate.m_ap == pytest.approx(5 / 6)
    assert per_class.precision == pytest.approx({"Text": 1 / 2, "Title": 1})
    assert per_class.f1_score == pytest.approx({"Text": 1 / 2, "Title": 1})
