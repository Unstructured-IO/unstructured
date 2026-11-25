import builtins

import numpy as np
import pytest

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import CoordinatesMetadata, ElementMetadata, Text
from unstructured.partition.utils import xycut
from unstructured.partition.utils.sorting import sort_page_elements


def pixel_projection(boxes, axis):
    result = np.zeros(np.max(boxes[:, axis::2]), dtype=np.int64)
    for box in boxes:
        for position in range(box[axis], box[axis + 2]):
            result[position] += 1
    return result


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("dtype", [np.int32, np.int64])
def test_projection_matches_pixel_counts_for_seeded_and_degenerate_boxes(axis, dtype):
    random = np.random.default_rng(48219)
    cases = [
        [[0, 0, 0, 0]],
        [[4, 4, 4, 4]],
        [[0, 0, 10, 10], [10, 10, 20, 20]],
        [[5, 6, 3, 2], [0, 0, 10, 10]],
        [[-3, -2, 3, 2], [0, 0, 10, 10]],
    ]
    cases.extend(random.integers(0, 120, size=(30, 4)) for _ in range(100))
    for values in cases:
        boxes = np.asarray(values, dtype=dtype)
        before = boxes.copy()
        np.testing.assert_array_equal(
            xycut.projection_by_bboxes(boxes, axis), pixel_projection(boxes, axis)
        )
        np.testing.assert_array_equal(boxes, before)


@pytest.mark.parametrize("axis", [0, 1])
def test_dense_projection_work_is_bounded_by_boxes_and_axis_length(monkeypatch, axis):
    boxes = np.tile(np.array([0, 0, 2000, 2000]), (100, 1))
    iterations = 0

    def counted_range(*args):
        nonlocal iterations
        values = builtins.range(*args)
        iterations += len(values)
        return values

    monkeypatch.setattr(xycut, "range", counted_range, raising=False)
    # The Python body measures deterministic work; benchmarks exercise the compiled path.
    result = xycut.projection_by_bboxes.py_func(boxes, axis)
    np.testing.assert_array_equal(result, np.full(2000, 100))
    assert iterations <= 3 * (len(boxes) + len(result))


@pytest.mark.parametrize("direction", ["x", "y"])
def test_public_page_sort_keeps_column_order_and_original_elements(direction):
    boxes = [(0, 0, 90, 20), (100, 0, 190, 20), (0, 40, 90, 60), (100, 40, 190, 60)]
    elements = []
    for index in [3, 1, 2, 0]:
        x0, y0, x1, y1 = boxes[index]
        metadata = ElementMetadata(
            coordinates=CoordinatesMetadata(
                ((x0, y0), (x0, y1), (x1, y1), (x1, y0)), PixelSpace(200, 100)
            )
        )
        elements.append(Text(str(index), metadata=metadata))
    result = sort_page_elements(elements, xy_cut_primary_direction=direction)
    assert [element.text for element in result] == (
        ["0", "2", "1", "3"] if direction == "x" else ["0", "1", "2", "3"]
    )
    assert {id(element) for element in result} == {id(element) for element in elements}
    assert [element.text for element in elements] == ["3", "1", "2", "0"]
