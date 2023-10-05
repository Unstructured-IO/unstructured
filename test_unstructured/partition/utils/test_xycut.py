import numpy as np
import pytest

from unstructured.partition.utils.xycut import (
    projection_by_bboxes,
    recursive_xy_cut,
    recursive_xy_cut_swapped,
    split_projection_profile,
)


def test_projection_by_bboxes():
    boxes = np.array([[10, 20, 50, 60], [30, 40, 70, 80]])

    # Test case 1: Horizontal projection
    result_horizontal = projection_by_bboxes(boxes, 0)
    expected_result_horizontal = np.array(
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    )
    assert np.array_equal(result_horizontal[:30], expected_result_horizontal)

    # Test case 2: Vertical projection
    result_vertical = projection_by_bboxes(boxes, 1)
    expected_result_vertical = np.array(
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    )
    assert np.array_equal(result_vertical[:30], expected_result_vertical)


def test_split_projection_profile():
    # Test case 1: Sample projection profile with given min_value and min_gap
    arr_values = np.array([0, 0, 3, 4, 0, 0, 2, 0, 0, 0, 5, 6, 7, 0, 0, 0])
    min_value = 0
    min_gap = 1
    result = split_projection_profile(arr_values, min_value, min_gap)
    expected_result = (np.array([2, 6, 10]), np.array([4, 7, 13]))
    assert np.array_equal(result, expected_result)

    # Test case 2: Another sample projection profile with different parameters
    arr_values = np.array([0, 2, 0, 0, 0, 3, 0, 0, 4, 5, 6, 0, 0, 0])
    min_value = 1
    min_gap = 2
    result = split_projection_profile(arr_values, min_value, min_gap)
    expected_result = (np.array([1, 5, 8]), np.array([2, 6, 11]))
    assert np.array_equal(result, expected_result)


@pytest.mark.parametrize(
    ("recursive_func", "expected"),
    [
        (recursive_xy_cut, [0, 1, 2]),
        (recursive_xy_cut_swapped, [0, 2, 1]),
    ],
)
def test_recursive_xy_cut(recursive_func, expected):
    boxes = np.array([[0, 0, 20, 20], [200, 0, 230, 30], [0, 40, 50, 50]])
    indices = np.array([0, 1, 2])
    res = []
    recursive_func(boxes, indices, res)
    assert res == expected
