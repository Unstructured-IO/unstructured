"""Positive-size text boxes survive the integer grid used by XY-cut sorting."""

import numpy as np
import pytest

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import CoordinatesMetadata, Text
from unstructured.partition.utils.sorting import (
    shrink_bbox,
    sort_bboxes_by_xy_cut,
    sort_page_elements,
)


@pytest.mark.parametrize("direction", ["x", "y"])
@pytest.mark.parametrize("size", [(1, 10), (10, 1), (1, 1)])
@pytest.mark.parametrize("order", [(0, 1, 2), (2, 0, 1)])
def test_thin_boxes_remain_in_the_sorted_permutation(direction, size, order):
    width, height = size
    boxes = np.array([(0, 0, 10, 10), (20, 20, 20 + width, 20 + height), (40, 40, 50, 50)])
    shuffled = boxes[list(order)]
    original = shuffled.copy()

    indexes = sort_bboxes_by_xy_cut(shuffled, xy_cut_primary_direction=direction)

    assert [order[index] for index in indexes] == [0, 1, 2]
    np.testing.assert_array_equal(shuffled, original)


@pytest.mark.parametrize("direction", ["x", "y"])
@pytest.mark.parametrize(
    ("box", "expected_indexes"),
    [
        ((20, 30, 21, 40), [0, 1, 2]),
        ((20, 30, 30, 31), [0, 1, 2]),
        ((20, 30, 21, 31), [0, 1, 2]),
        ((20.2, 30.2, 20.8, 40.2), [0, 1, 2]),
        ((20.2, 30.2, 30.2, 30.8), [0, 1, 2]),
        ((20.2, 30.2, 20.8, 30.8), [0, 1, 2]),
        ((20.2, 30.2, 20.2, 40.2), [0, 2]),
        ((20.2, 30.2, 30.2, 30.2), [0, 2]),
        ((20.2, 30.2, 20.2, 30.2), [0, 2]),
    ],
)
def test_sorting_real_page_elements_preserves_positive_extents_only(
    direction, box, expected_indexes
):
    boxes = [(0, 0, 10, 10), box, (40, 50, 50, 60)]
    elements = []
    for index, (left, top, right, bottom) in enumerate(boxes):
        element = Text(text=f"part {index}")
        element.metadata.coordinates = CoordinatesMetadata(
            points=((left, top), (left, bottom), (right, bottom), (right, top)),
            system=PixelSpace(width=100, height=100),
        )
        elements.append(element)
    coordinates = [element.metadata.coordinates.to_dict() for element in elements]

    result = sort_page_elements(
        [elements[2], elements[0], elements[1]], xy_cut_primary_direction=direction
    )

    assert [element.text for element in result] == [f"part {index}" for index in expected_indexes]
    assert all(actual is elements[index] for actual, index in zip(result, expected_indexes))
    assert [element.metadata.coordinates.to_dict() for element in elements] == coordinates


@pytest.mark.parametrize(
    ("box", "factor", "expected"),
    [
        ((20, 30, 21, 40), 0.9, (20, 30, 21, 39)),
        ((20, 30, 30, 31), 0.9, (20, 30, 29, 31)),
        ((20, 30, 21, 31), 0.1, (20, 30, 21, 31)),
        ((20.2, 30.2, 20.8, 30.8), 0.9, (20, 30, 21, 31)),
        ((20, 30, 30, 40), 0.9, (20, 30, 29, 39)),
        ((20, 30, 21, 31), 1.0, (20, 30, 21, 31)),
        ((20, 30, 30, 40), 0.0, (20, 30, 20, 30)),
        ((20, 30, 20, 30), 0.9, (20, 30, 20, 30)),
    ],
)
def test_integer_shrinking_preserves_positive_extents_only(box, factor, expected):
    assert shrink_bbox(box, factor) == expected
