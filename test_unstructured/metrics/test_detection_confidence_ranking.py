"""Confidence ranking retains zero scores and preserves the order of tied detections."""

import pytest
import torch

from unstructured.metrics.object_detection import ObjectDetectionEvalProcessor


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64, torch.int64])
@pytest.mark.parametrize(
    ("predictions", "precision", "recall", "f1", "ap"),
    [
        ([[0, 0, 10, 10, 0, 0]], 1, 1, 1, 1),
        ([[0, 0, 10, 10, 1, 0], [50, 50, 60, 60, 0, 0]], 1 / 2, 1, 2 / 3, 1),
        ([[50, 50, 60, 60, 1, 0], [0, 0, 10, 10, 0, 0]], 1 / 2, 1, 2 / 3, 1 / 2),
    ],
)
def test_zero_score_detections_contribute_to_metrics(dtype, predictions, precision, recall, f1, ap):
    processor = ObjectDetectionEvalProcessor(
        [torch.tensor(predictions, dtype=dtype)],
        [torch.tensor([[0, 0, 0, 10, 10]], dtype=dtype)],
        [100],
        [100],
        ["Text"],
    )
    processor.score_threshold = 0.0

    aggregate, per_class = processor.get_metrics()

    assert vars(aggregate) == pytest.approx(
        {"precision": precision, "recall": recall, "f1_score": f1, "m_ap": ap}
    )
    assert per_class.precision == pytest.approx({"Text": precision})
    assert per_class.recall == pytest.approx({"Text": recall})
    assert per_class.f1_score == pytest.approx({"Text": f1})
    assert per_class.m_ap == pytest.approx({"Text": ap})


def test_zero_score_detection_still_contributes_to_ap_below_the_score_threshold():
    processor = ObjectDetectionEvalProcessor(
        [torch.tensor([[50, 50, 60, 60, 0.9, 0], [0, 0, 10, 10, 0, 0]])],
        [torch.tensor([[0, 0, 0, 10, 10]])],
        [100],
        [100],
        ["Text"],
    )

    aggregate, _ = processor.get_metrics()

    assert vars(aggregate) == pytest.approx(
        {"precision": 0, "recall": 0, "f1_score": 0, "m_ap": 1 / 2}
    )


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64, torch.int64])
@pytest.mark.parametrize(
    ("top_k", "expected"),
    [(0, []), (1, [1, 3]), (2, [0, 1, 2, 3]), (100, [0, 1, 2, 3, 4, 5])],
)
def test_top_k_counts_real_detections_in_each_class(dtype, top_k, expected):
    scores = torch.tensor([0, 1, 0, 1, 0, 0], dtype=dtype)
    classes = torch.tensor([0, 2, 2, 0, 2, 0])

    selected = ObjectDetectionEvalProcessor._get_top_k_idx_per_cls(scores, classes, top_k)

    assert selected.sort().values.tolist() == expected


def test_top_k_keeps_the_first_tied_detections_for_each_class():
    scores = torch.full((32,), 0.5)
    classes = torch.tensor([0, 2] * 16)

    selected = ObjectDetectionEvalProcessor._get_top_k_idx_per_cls(scores, classes, top_k=2)

    assert selected.sort().values.tolist() == [0, 1, 2, 3]


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize("true_positive_index", [0, 31])
def test_average_precision_preserves_the_input_order_of_equal_scores(dtype, true_positive_index):
    predictions = torch.tensor([[50, 50, 60, 60, 0.5, 0]] * 32, dtype=dtype)
    predictions[true_positive_index, :4] = torch.tensor([0, 0, 10, 10])
    processor = ObjectDetectionEvalProcessor(
        [predictions], [torch.tensor([[0, 0, 0, 10, 10]])], [100], [100], ["Text"]
    )

    aggregate, per_class = processor.get_metrics()

    # A single target reaches full recall at the original position of its detection.
    # The interpolated precision envelope is constant at this value over all recall samples.
    expected_ap = 1 / (true_positive_index + 1)
    assert aggregate.m_ap == pytest.approx(expected_ap)
    assert per_class.m_ap == pytest.approx({"Text": expected_ap})
    assert aggregate.precision == pytest.approx(1 / 32)
    assert aggregate.recall == pytest.approx(1)


def test_target_matching_gives_the_first_tied_detection_priority():
    predictions = torch.tensor([[50, 50, 60, 60, 0.5, 0]] * 32)
    predictions[0, :4] = predictions[31, :4] = torch.tensor([0, 0, 10, 10])
    targets = torch.tensor([[0, 0, 0, 10, 10]])
    processor = ObjectDetectionEvalProcessor([predictions], [targets], [100], [100], ["Text"])

    matched, _, _, _, _ = processor._compute_page_detection_matching(
        predictions, targets, height=100, width=100
    )

    assert matched[0].all()
    assert not matched[31].any()
    assert matched.sum(dim=0).tolist() == [1] * len(processor.iou_thresholds)
