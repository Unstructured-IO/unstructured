from unittest.mock import patch

import cv2
import numpy as np
import pytest

from unstructured.partition.utils import xycut


def test_projection_by_bboxes():
    boxes = np.array([[10, 20, 50, 60], [30, 40, 70, 80]])

    # Test case 1: Horizontal projection
    result_horizontal = xycut.projection_by_bboxes(boxes, 0)
    expected_result_horizontal = np.array(
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    )
    assert np.array_equal(result_horizontal[:30], expected_result_horizontal)

    # Test case 2: Vertical projection
    result_vertical = xycut.projection_by_bboxes(boxes, 1)
    expected_result_vertical = np.array(
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    )
    assert np.array_equal(result_vertical[:30], expected_result_vertical)


def test_split_projection_profile():
    # Test case 1: Sample projection profile with given min_value and min_gap
    arr_values = np.array([0, 0, 3, 4, 0, 0, 2, 0, 0, 0, 5, 6, 7, 0, 0, 0])
    min_value = 0
    min_gap = 1
    result = xycut.split_projection_profile(arr_values, min_value, min_gap)
    expected_result = (np.array([2, 6, 10]), np.array([4, 7, 13]))
    assert np.array_equal(result, expected_result)

    # Test case 2: Another sample projection profile with different parameters
    arr_values = np.array([0, 2, 0, 0, 0, 3, 0, 0, 4, 5, 6, 0, 0, 0])
    min_value = 1
    min_gap = 2
    result = xycut.split_projection_profile(arr_values, min_value, min_gap)
    expected_result = (np.array([1, 5, 8]), np.array([2, 6, 11]))
    assert np.array_equal(result, expected_result)


@pytest.mark.parametrize(
    ("recursive_func", "expected"),
    [
        (xycut.recursive_xy_cut, [0, 1, 2]),
        (xycut.recursive_xy_cut_swapped, [0, 2, 1]),
    ],
)
def test_recursive_xy_cut(recursive_func, expected):
    boxes = np.array([[0, 0, 20, 20], [200, 0, 230, 30], [0, 40, 50, 50]])
    indices = np.array([0, 1, 2])
    res = []
    recursive_func(boxes, indices, res)
    assert res == expected


def test_points_to_bbox():
    # Test a valid case
    points = [10, 20, 30, 40, 50, 60, 70, 80]
    result = xycut.points_to_bbox(points)
    assert result == [10, 20, 70, 80]

    # Test a case where points are unordered
    points = [30, 40, 10, 20, 70, 80, 50, 60]
    result = xycut.points_to_bbox(points)
    assert result == [10, 20, 70, 80]

    # Test a case where all points are negative
    points = [-10, -20, -30, -40, -50, -60, -70, -80]
    result = xycut.points_to_bbox(points)
    assert result == [0, 0, 0, 0]

    # Test a case with invalid number of points
    with pytest.raises(AssertionError):
        points = [10, 20, 30, 40, 50, 60]  # Missing two points
        xycut.points_to_bbox(points)


def test_bbox2points():
    # Test a valid case
    bbox = [10, 20, 70, 80]
    result = xycut.bbox2points(bbox)
    assert result == [10, 20, 70, 20, 70, 80, 10, 80]

    # Test a case where the top and bottom are the same
    bbox = [10, 20, 70, 20]
    result = xycut.bbox2points(bbox)
    assert result == [10, 20, 70, 20, 70, 20, 10, 20]

    # Test a case where left and right are the same
    bbox = [10, 20, 10, 80]
    result = xycut.bbox2points(bbox)
    assert result == [10, 20, 10, 20, 10, 80, 10, 80]

    # Test a case where the bbox is a point (left and right are the same,
    # top and bottom are the same)
    bbox = [10, 20, 10, 20]
    result = xycut.bbox2points(bbox)
    assert result == [10, 20, 10, 20, 10, 20, 10, 20]


def test_vis_polygon():
    img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    points = [(50, 50), (150, 50), (150, 150), (50, 150)]
    color = (0, 0, 255)  # Red color
    thickness = 2

    result_img = xycut.vis_polygon(img, points, thickness, color)

    # Define the expected image with the square drawn
    expected_img = np.copy(img)
    cv2.line(expected_img, points[0], points[1], color, thickness)
    cv2.line(expected_img, points[1], points[2], color, thickness)
    cv2.line(expected_img, points[2], points[3], color, thickness)
    cv2.line(expected_img, points[3], points[0], color, thickness)

    assert np.array_equal(result_img, expected_img)


def test_vis_points():
    img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    points = [[10, 20, 30, 20, 30, 40, 10, 40], [50, 60, 70, 60, 70, 80, 50, 80]]
    texts = ["Label1", "Label2"]
    color = (0, 200, 0)

    result_img = xycut.vis_points(img, points, texts, color)

    # Check if the resulting image contains the expected shapes and labels
    expected_img = np.copy(img)

    # Draw polygons and labels for each set of points
    for i, _points in enumerate(points):
        xycut.vis_polygon(expected_img, np.array(_points).reshape(-1, 2), thickness=2, color=color)
        bbox = xycut.points_to_bbox(_points)
        left, top, right, bottom = bbox
        cx = (left + right) // 2
        cy = (top + bottom) // 2
        txt = texts[i]

        # Draw a filled rectangle for the label background
        cat_size = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        expected_img = cv2.rectangle(
            expected_img,
            (cx - 5 * len(txt), cy - cat_size[1] - 5),
            (cx - 5 * len(txt) + cat_size[0], cy - 5),
            color,
            -1,
        )

        # Draw the label text
        expected_img = cv2.putText(
            expected_img,
            txt,
            (cx - 5 * len(txt), cy - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            thickness=1,
            lineType=cv2.LINE_AA,
        )

    assert np.array_equal(result_img, expected_img)


def test_vis_polygons_with_index():
    img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    points = [[10, 20, 30, 20, 30, 40, 10, 40], [50, 60, 70, 60, 70, 80, 50, 80]]

    with patch(
        "unstructured.partition.utils.xycut.vis_points", return_value=img
    ) as mock_vis_points:
        result_img = xycut.vis_polygons_with_index(img, points)

        # Check if vis_points was called with the correct arguments
        mock_vis_points.assert_called_once()

        assert np.array_equal(result_img, img)
