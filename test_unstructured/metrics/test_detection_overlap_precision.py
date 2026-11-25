"""Detection overlap arithmetic retains the precision of supported coordinate tensors."""

import pytest
import torch

from unstructured.metrics.object_detection import ObjectDetectionEvalProcessor


@pytest.mark.parametrize(
    ("prediction_dtype", "target_dtype", "width", "height", "target_width", "expected"),
    [
        pytest.param(torch.float16, torch.float16, 200, 200, 200, 1, id="half-union-overflow"),
        pytest.param(torch.float16, torch.float16, 512, 512, 512, 1, id="half-area-overflow"),
        pytest.param(torch.float16, torch.float32, 512, 512, 512, 1, id="half-predictions"),
        pytest.param(torch.float32, torch.float16, 512, 512, 512, 1, id="half-targets"),
        pytest.param(torch.float16, torch.float64, 512, 512, 512, 1, id="half-double"),
        pytest.param(torch.float64, torch.float16, 512, 512, 512, 1, id="double-half"),
        pytest.param(torch.bfloat16, torch.bfloat16, 101, 200, 86, 0.8, id="bfloat-rounding"),
        pytest.param(torch.bfloat16, torch.float32, 101, 200, 86, 0.8, id="bfloat-predictions"),
        pytest.param(torch.float32, torch.bfloat16, 101, 200, 86, 0.8, id="bfloat-targets"),
        pytest.param(torch.float32, torch.uint8, 200, 200, 148, 0.5, id="unsigned-target-area"),
        pytest.param(torch.float32, torch.int8, 100, 100, 74, 0.5, id="signed-byte-target-area"),
        pytest.param(torch.float32, torch.int16, 200, 200, 200, 1, id="short-target-area"),
        pytest.param(torch.float32, torch.int32, 50000, 50000, 50000, 1, id="int-target-area"),
        pytest.param(torch.float32, torch.float32, 512, 512, 512, 1, id="float-control"),
        pytest.param(torch.float64, torch.float64, 512, 512, 512, 1, id="double-control"),
        pytest.param(torch.float32, torch.int64, 50000, 50000, 50000, 1, id="long-control"),
    ],
)
def test_detection_metrics_preserve_narrow_coordinate_arithmetic(
    prediction_dtype, target_dtype, width, height, target_width, expected
):
    """Match real tensor inputs without overflowing areas or rounding across IoU thresholds."""
    predictions = torch.tensor([[0, 0, width, height, 0.9, 0]], dtype=prediction_dtype)
    targets = torch.tensor([[0, 0, 0, target_width, height]], dtype=target_dtype)
    original_predictions = predictions.clone()
    original_targets = targets.clone()
    processor = ObjectDetectionEvalProcessor([predictions], [targets], [height], [width], ["Text"])

    aggregate, per_class = processor.get_metrics()

    # For one prediction and one target, each accepted IoU threshold contributes
    # 1 to all four metrics. IoUs 86/101 and 0.74 meet eight and five thresholds.
    for metric in ("precision", "recall", "f1_score", "m_ap"):
        assert getattr(aggregate, metric) == pytest.approx(expected)
        assert getattr(per_class, metric) == pytest.approx({"Text": expected})
    torch.testing.assert_close(predictions, original_predictions, rtol=0, atol=0)
    torch.testing.assert_close(targets, original_targets, rtol=0, atol=0)


@pytest.mark.parametrize(
    "dtype",
    [
        torch.float16,
        torch.bfloat16,
        torch.uint8,
        torch.int8,
        torch.int16,
        torch.int32,
        torch.int64,
        torch.float32,
        torch.float64,
    ],
)
def test_pairwise_overlaps_preserve_fractional_areas_and_input_views(dtype):
    """Compute hand-calculated overlaps for overlapping, contained, and disjoint boxes."""
    first = torch.tensor([[0, 0, 100, 100], [10, 20, 60, 80]], dtype=dtype)
    second = torch.tensor([[0, 0, 100, 100], [0, 0, 50, 100], [110, 0, 120, 100]], dtype=dtype)
    # Preserve a caller's strided view into larger coordinate storage.
    first_storage = torch.zeros((2, 8), dtype=dtype)
    first_storage[:, ::2] = first
    first_view = first_storage[:, ::2]
    original_storage = first_storage.clone()
    original_second = second.clone()
    expected_dtype = torch.float64 if dtype == torch.float64 else torch.float32
    expected = torch.tensor([[1, 0.5, 0], [0.3, 3 / 7, 0]], dtype=expected_dtype)

    result = ObjectDetectionEvalProcessor._box_iou(first_view, second)

    torch.testing.assert_close(result, expected)
    torch.testing.assert_close(first_storage, original_storage, rtol=0, atol=0)
    torch.testing.assert_close(second, original_second, rtol=0, atol=0)


@pytest.mark.parametrize("dtype", [torch.float64, torch.int64])
def test_wide_coordinate_types_preserve_small_differences_at_large_offsets(dtype):
    """Avoid a float32 conversion that would erase valid double/long coordinate differences."""
    offset = 2**40
    first = torch.tensor([[offset, offset, offset + 3, offset + 7]], dtype=dtype)
    second = torch.tensor([[offset + 1, offset, offset + 4, offset + 7]], dtype=dtype)
    expected_dtype = torch.float64 if dtype == torch.float64 else torch.float32

    result = ObjectDetectionEvalProcessor._box_iou(first, second)

    torch.testing.assert_close(result, torch.tensor([[0.5]], dtype=expected_dtype))


@pytest.mark.parametrize(("first_count", "second_count"), [(0, 1), (1, 0), (0, 0)])
def test_empty_half_precision_boxes_preserve_pairwise_result_shape(first_count, second_count):
    """Keep empty-pair behavior when promoting coordinates for safe area arithmetic."""
    first = torch.zeros((first_count, 4), dtype=torch.float16)
    second = torch.zeros((second_count, 4), dtype=torch.float16)

    result = ObjectDetectionEvalProcessor._box_iou(first, second)

    assert result.shape == (first_count, second_count)
    assert result.numel() == 0
