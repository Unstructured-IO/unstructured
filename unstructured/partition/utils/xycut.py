from typing import List, Optional, Tuple

import numpy as np
from numba import njit

from unstructured.utils import requires_dependencies

"""
This module contains an improved implementation of the XY-Cut sorting approach.
Modified to better handle academic papers with thin column gaps and noise.
"""


@njit(cache=True)
def projection_by_bboxes(boxes: np.ndarray, axis: int) -> np.ndarray:
    """
    Obtain the projection histogram through a set of bboxes and finally output it in per-pixel form
    """
    assert axis in [0, 1]
    if boxes.shape[0] == 0:
        return np.zeros(0, dtype=np.int64)

    length = np.max(boxes[:, axis::2])
    res = np.zeros(length, dtype=np.int64)
    for i in range(boxes.shape[0]):
        start = boxes[i, axis]
        end = boxes[i, axis + 2]
        for j in range(start, end):
            if j < length:
                res[j] += 1
    return res


@njit(cache=True)
def split_projection_profile(arr_values: np.ndarray, min_value: float, min_gap: float):
    """
    Split projection profile with noise filtering (min_value) and gap thresholding (min_gap).
    """
    # FIX: Noise filtering - ignore small peaks that are usually scanning noise or math symbols
    arr_index = np.where(arr_values > min_value)[0]
    if not len(arr_index):
        return None

    # find intervals between adjacent projections
    arr_diff = arr_index[1:] - arr_index[0:-1]
    
    # FIX: Academic columns have narrow but consistent gaps. Increased threshold for stability.
    arr_diff_index = np.where(arr_diff > min_gap)[0]
    arr_zero_intvl_start = arr_index[arr_diff_index]
    arr_zero_intvl_end = arr_index[arr_diff_index + 1]

    # convert to index of projection range:
    arr_start = np.empty(arr_zero_intvl_end.shape[0] + 1, dtype=arr_zero_intvl_end.dtype)
    arr_end = np.empty(arr_zero_intvl_start.shape[0] + 1, dtype=arr_zero_intvl_start.dtype)
    arr_start[0] = arr_index[0]
    for i in range(arr_zero_intvl_end.shape[0]):
        arr_start[i + 1] = arr_zero_intvl_end[i]
    for i in range(arr_zero_intvl_start.shape[0]):
        arr_end[i] = arr_zero_intvl_start[i]
    arr_end[-1] = arr_index[-1]
    arr_end += 1  # end index will be excluded as index slice

    return arr_start, arr_end


def recursive_xy_cut(boxes: np.ndarray, indices: np.ndarray, res: List[int]):
    """
    Recursive XY-Cut: Top-down approach. Improved for academic papers.
    """
    assert len(boxes) == len(indices)
    if len(boxes) == 0:
        return

    # project to the y-axis
    _indices = boxes[:, 1].argsort()
    y_sorted_boxes = boxes[_indices]
    y_sorted_indices = indices[_indices]

    y_projection = projection_by_bboxes(boxes=y_sorted_boxes, axis=1)
    # FIX: Increased min_gap to 2 for lines to avoid splitting characters with descenders
    pos_y = split_projection_profile(y_projection, min_value=0, min_gap=2)
    
    if not pos_y:
        res.extend(y_sorted_indices)
        return

    arr_y0, arr_y1 = pos_y
    for r0, r1 in zip(arr_y0, arr_y1):
        _indices = (r0 <= y_sorted_boxes[:, 1]) & (y_sorted_boxes[:, 1] < r1)
        y_sorted_boxes_chunk = y_sorted_boxes[_indices]
        y_sorted_indices_chunk = y_sorted_indices[_indices]

        if len(y_sorted_boxes_chunk) == 0:
            continue

        _indices = y_sorted_boxes_chunk[:, 0].argsort()
        x_sorted_boxes_chunk = y_sorted_boxes_chunk[_indices]
        x_sorted_indices_chunk = y_sorted_indices_chunk[_indices]

        # project in the x direction
        x_projection = projection_by_bboxes(boxes=x_sorted_boxes_chunk, axis=0)
        # FIX: Aggressive column gap detection for academic papers
        pos_x = split_projection_profile(x_projection, min_value=1, min_gap=10)
        
        if not pos_x or len(pos_x[0]) == 1:
            res.extend(x_sorted_indices_chunk)
            continue

        # can be separated in the x-direction and continue to call recursively
        for c0, c1 in zip(pos_x[0], pos_x[1]):
            _indices = (c0 <= x_sorted_boxes_chunk[:, 0]) & (x_sorted_boxes_chunk[:, 0] < c1)
            recursive_xy_cut(
                x_sorted_boxes_chunk[_indices],
                x_sorted_indices_chunk[_indices],
                res,
            )


def recursive_xy_cut_swapped(boxes: np.ndarray, indices: np.ndarray, res: List[int]):
    """
    Recursive XY-Cut: Left-right primary approach. Improved for academic columns.
    """
    assert len(boxes) == len(indices)
    if len(boxes) == 0:
        return

    _indices = boxes[:, 0].argsort()
    x_sorted_boxes = boxes[_indices]
    x_sorted_indices = indices[_indices]

    x_projection = projection_by_bboxes(boxes=x_sorted_boxes, axis=0)
    # FIX: Using 15px gap to robustly identify column gutters in research papers
    pos_x = split_projection_profile(x_projection, min_value=1, min_gap=15)

    if not pos_x:
        res.extend(x_sorted_indices)
        return

    arr_x0, arr_x1 = pos_x
    for c0, c1 in zip(arr_x0, arr_x1):
        _indices = (c0 <= x_sorted_boxes[:, 0]) & (x_sorted_boxes[:, 0] < c1)
        x_sorted_boxes_chunk = x_sorted_boxes[_indices]
        x_sorted_indices_chunk = x_sorted_indices[_indices]

        if len(x_sorted_boxes_chunk) == 0:
            continue

        _indices = x_sorted_boxes_chunk[:, 1].argsort()
        y_sorted_boxes_chunk = x_sorted_boxes_chunk[_indices]
        y_sorted_indices_chunk = x_sorted_indices_chunk[_indices]

        y_projection = projection_by_bboxes(boxes=y_sorted_boxes_chunk, axis=1)
        pos_y = split_projection_profile(y_projection, min_value=0, min_gap=2)

        if not pos_y or len(pos_y[0]) == 1:
            res.extend(y_sorted_indices_chunk)
            continue

        arr_y0, arr_y1 = pos_y
        for r0, r1 in zip(arr_y0, arr_y1):
            _indices = (r0 <= y_sorted_boxes_chunk[:, 1]) & (y_sorted_boxes_chunk[:, 1] < r1)
            recursive_xy_cut_swapped(
                y_sorted_boxes_chunk[_indices],
                y_sorted_indices_chunk[_indices],
                res,
            )


def points_to_bbox(points):
    """Convert points to bbox [left, top, right, bottom]"""
    if len(points) == 8:
        left = min(points[::2])
        right = max(points[::2])
        top = min(points[1::2])
        bottom = max(points[1::2])
    else:
        left, top, right, bottom = points

    return [max(left, 0), max(top, 0), max(right, 0), max(bottom, 0)]


def bbox2points(bbox):
    left, top, right, bottom = bbox
    return [left, top, right, top, right, bottom, left, bottom]


@requires_dependencies("cv2")
def vis_polygon(img, points, thickness=2, color=None):
    import cv2
    color = (0, 255, 0) if color is None else color
    pts = points.reshape((-1, 1, 2)).astype(np.int32)
    cv2.polylines(img, [pts], True, color, thickness)
    return img


@requires_dependencies("cv2")
def vis_points(img: np.ndarray, points, texts: List[str], color=(0, 200, 0)) -> np.ndarray:
    import cv2
    points = np.array(points)
    assert len(texts) == points.shape[0]

    for i, _points in enumerate(points):
        vis_polygon(img, _points.reshape(-1, 2), thickness=2, color=color)
        bbox = points_to_bbox(_points)
        left, top, right, bottom = bbox
        cx, cy = (left + right) // 2, (top + bottom) // 2

        txt = texts[i]
        font = cv2.FONT_HERSHEY_SIMPLEX
        cat_size = cv2.getTextSize(txt, font, 0.5, 2)[0]
        img = cv2.rectangle(img, (cx - 5 * len(txt), cy - cat_size[1] - 5), 
                            (cx - 5 * len(txt) + cat_size[0], cy - 5), color, -1)
        img = cv2.putText(img, txt, (cx - 5 * len(txt), cy - 5), font, 0.5, (255, 255, 255), 1)
    return img


def vis_polygons_with_index(image, points):
    texts = [str(i) for i in range(len(points))]
    return vis_points(image.copy(), points, texts)