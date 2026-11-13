"""Detection evaluation clips local boxes without modifying model predictions."""

import pytest
import torch

from unstructured.metrics.object_detection import ObjectDetectionEvalProcessor


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize("box", [(-10, -5, 120, 140), (10, 20, 80, 90)])
@pytest.mark.parametrize("strided", [False, True])
def test_evaluation_preserves_caller_owned_predictions(dtype, box, strided):
    original = torch.tensor([[*box, 0.9, 0]], dtype=dtype)
    storage = torch.full((1, 12), -99, dtype=dtype)
    storage[:, ::2] = original
    predictions = storage[:, ::2] if strided else original.clone()
    prediction_snapshot = predictions.clone()
    storage_snapshot = storage.clone()
    bounded_box = [max(0, min(100, value)) for value in box]
    targets = torch.tensor([[0, *bounded_box]], dtype=dtype)
    target_snapshot = targets.clone()
    processor = ObjectDetectionEvalProcessor([predictions], [targets], [100], [100], ["Text"])

    aggregate, _ = processor.get_metrics()

    assert vars(aggregate) == pytest.approx({"precision": 1, "recall": 1, "f1_score": 1, "m_ap": 1})
    torch.testing.assert_close(predictions, prediction_snapshot, rtol=0, atol=0)
    torch.testing.assert_close(storage, storage_snapshot, rtol=0, atol=0)
    torch.testing.assert_close(targets, target_snapshot, rtol=0, atol=0)


@pytest.mark.parametrize("dimensions", [(50, 100), (100, 50)])
def test_prediction_reuse_does_not_depend_on_the_previous_page_size(dimensions):
    predictions = torch.tensor([[-10, -10, 120, 120, 0.9, 0]])
    original = predictions.clone()

    for size in dimensions:
        targets = torch.tensor([[0, 0, 0, size, size]])
        processor = ObjectDetectionEvalProcessor([predictions], [targets], [size], [size], ["Text"])

        aggregate, _ = processor.get_metrics()

        assert vars(aggregate) == pytest.approx(
            {"precision": 1, "recall": 1, "f1_score": 1, "m_ap": 1}
        )

    torch.testing.assert_close(predictions, original, rtol=0, atol=0)


def test_a_page_without_targets_keeps_the_original_prediction_values():
    predictions = torch.tensor([[-10, -5, 120, 140, 0.9, 0]])
    original = predictions.clone()
    processor = ObjectDetectionEvalProcessor(
        [predictions], [torch.empty(0, 5)], [100], [100], ["Text"]
    )

    processor.get_metrics()

    torch.testing.assert_close(predictions, original, rtol=0, atol=0)
