"""An IoU threshold includes detections whose overlap is exactly at the boundary."""

import pytest
import torch

from unstructured.metrics.object_detection import ObjectDetectionEvalProcessor


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize(
    ("prediction_width", "threshold", "expected"),
    [(0.49, 0.5, 0), (0.5, 0.5, 1), (0.51, 0.5, 1), (1.0, 1.0, 1)],
)
def test_detection_iou_threshold_is_inclusive(dtype, prediction_width, threshold, expected):
    """Public document metrics include the boundary and still reject smaller overlaps."""
    predictions = torch.tensor([[0, 0, prediction_width, 1, 0.9, 0]], dtype=dtype)
    targets = torch.tensor([[0, 0, 0, 1, 1]], dtype=dtype)
    processor = ObjectDetectionEvalProcessor([predictions], [targets], [10], [10], ["Text"])
    processor.iou_thresholds = torch.tensor([threshold], dtype=dtype)

    aggregate, per_class = processor.get_metrics()

    assert vars(aggregate) == pytest.approx(
        {"precision": expected, "recall": expected, "f1_score": expected, "m_ap": expected}
    )
    assert per_class.m_ap == pytest.approx({"Text": expected})


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize(("prediction_width", "expected"), [(0.5, 0.1), (0.75, 0.6), (1, 1)])
def test_default_detection_metrics_count_the_equal_iou_threshold(dtype, prediction_width, expected):
    """The default 0.50:0.95 average includes each threshold the overlap reaches."""
    predictions = torch.tensor([[0, 0, prediction_width, 1, 0.9, 0]], dtype=dtype)
    targets = torch.tensor([[0, 0, 0, 1, 1]], dtype=dtype)
    processor = ObjectDetectionEvalProcessor([predictions], [targets], [10], [10], ["Text"])

    aggregate, _ = processor.get_metrics()

    assert vars(aggregate) == pytest.approx(
        {"precision": expected, "recall": expected, "f1_score": expected, "m_ap": expected}
    )


def test_zero_iou_threshold_still_excludes_a_different_class():
    """An excluded-class detection must not consume the target before the right class."""
    predictions = torch.tensor([[0, 0, 1, 1, 0.99, 0], [0, 0, 1, 1, 0.9, 1]])
    targets = torch.tensor([[1, 0, 0, 1, 1]])
    processor = ObjectDetectionEvalProcessor(
        [predictions], [targets], [10], [10], ["Text", "Title"]
    )
    processor.iou_thresholds = torch.tensor([0.0])

    aggregate, per_class = processor.get_metrics()

    assert vars(aggregate) == pytest.approx({"precision": 1, "recall": 1, "f1_score": 1, "m_ap": 1})
    assert per_class.m_ap["Title"] == pytest.approx(1)


def test_zero_iou_threshold_accepts_same_class_zero_overlap():
    """The lower endpoint follows the same inclusive comparison for valid same-class boxes."""
    predictions = torch.tensor([[2, 0, 3, 1, 0.9, 0]])
    targets = torch.tensor([[0, 0, 0, 1, 1]])
    processor = ObjectDetectionEvalProcessor([predictions], [targets], [10], [10], ["Text"])
    processor.iou_thresholds = torch.tensor([0.0])

    aggregate, _ = processor.get_metrics()

    assert vars(aggregate) == pytest.approx({"precision": 1, "recall": 1, "f1_score": 1, "m_ap": 1})
