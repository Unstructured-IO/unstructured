from typing import List

import numpy as np

from unstructured.utils import requires_dependencies

"""

This module contains the implementation of the XY-Cut sorting approach
from: https://github.com/Sanster/xy-cut

"""


def projection_by_bboxes(boxes: np.ndarray, axis: int) -> np.ndarray:
    """
    Obtain the projection histogram through a set of bboxes and finally output it in per-pixel form

    Args:
        boxes: [N, 4]
        axis: 0 - x coordinates are projected in the horizontal direction, 1 - y coordinates
        are projected in the vertical direction

    Returns:
        1D projection histogram, the length is the maximum value of the projection direction
        coordinate (we don’t need the actual side length of the picture because we just
        want to find the interval of the text box)
    """

    assert axis in [0, 1]
    length = np.max(boxes[:, axis::2])
    res = np.zeros(length, dtype=int)
    # TODO: how to remove for loop?
    for start, end in boxes[:, axis::2]:
        res[start:end] += 1
    return res


# from: https://dothinking.github.io/2021-06-19-%E9%80%92%E5%BD%92%E6%8A%95%E5%BD%B1
# %E5%88%86%E5%89%B2%E7%AE%97%E6%B3%95/#:~:text=%E9%80%92%E5%BD%92%E6%8A%95%E5%BD%B1
# %E5%88%86%E5%89%B2%EF%BC%88Recursive%20XY,%EF%BC%8C%E5%8F%AF%E4%BB%A5%E5%88%92
# %E5%88%86%E6%AE%B5%E8%90%BD%E3%80%81%E8%A1%8C%E3%80%82
def split_projection_profile(arr_values: np.ndarray, min_value: float, min_gap: float):
    """Split projection profile:

    ```
                              ┌──┐
         arr_values           │  │       ┌─┐───
             ┌──┐             │  │       │ │ |
             │  │             │  │ ┌───┐ │ │min_value
             │  │<- min_gap ->│  │ │   │ │ │ |
         ────┴──┴─────────────┴──┴─┴───┴─┴─┴─┴───
         0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16
    ```

    Args:
        arr_values (np.array): 1-d array representing the projection profile.
        min_value (float): Ignore the profile if `arr_value` is less than `min_value`.
        min_gap (float): Ignore the gap if less than this value.

    Returns:
        tuple: Start indexes and end indexes of split groups.
    """
    # all indexes with projection height exceeding the threshold
    arr_index = np.where(arr_values > min_value)[0]
    if not len(arr_index):
        return

    # find zero intervals between adjacent projections
    # |  |                    ||
    # ||||<- zero-interval -> |||||
    arr_diff = arr_index[1:] - arr_index[0:-1]
    arr_diff_index = np.where(arr_diff > min_gap)[0]
    arr_zero_intvl_start = arr_index[arr_diff_index]
    arr_zero_intvl_end = arr_index[arr_diff_index + 1]

    # convert to index of projection range:
    # the start index of zero interval is the end index of projection
    arr_start = np.insert(arr_zero_intvl_end, 0, arr_index[0])
    arr_end = np.append(arr_zero_intvl_start, arr_index[-1])
    arr_end += 1  # end index will be excluded as index slice

    return arr_start, arr_end


def recursive_xy_cut(boxes: np.ndarray, indices: np.ndarray, res: List[int]):
    """

    Args:
        boxes: (N, 4)
        indices: during the recursion process, the index of box in the original data
         is always represented.
        res: save output

    """
    # project to the y-axis
    assert len(boxes) == len(indices)

    _indices = boxes[:, 1].argsort()
    y_sorted_boxes = boxes[_indices]
    y_sorted_indices = indices[_indices]

    # debug_vis(y_sorted_boxes, y_sorted_indices)

    y_projection = projection_by_bboxes(boxes=y_sorted_boxes, axis=1)
    pos_y = split_projection_profile(y_projection, 0, 1)
    if not pos_y:
        return

    arr_y0, arr_y1 = pos_y
    for r0, r1 in zip(arr_y0, arr_y1):
        # [r0, r1] means that the areas with bbox will be divided horizontally, and these areas
        # will be divided vertically.
        _indices = (r0 <= y_sorted_boxes[:, 1]) & (y_sorted_boxes[:, 1] < r1)

        y_sorted_boxes_chunk = y_sorted_boxes[_indices]
        y_sorted_indices_chunk = y_sorted_indices[_indices]

        _indices = y_sorted_boxes_chunk[:, 0].argsort()
        x_sorted_boxes_chunk = y_sorted_boxes_chunk[_indices]
        x_sorted_indices_chunk = y_sorted_indices_chunk[_indices]

        # project in the x direction
        x_projection = projection_by_bboxes(boxes=x_sorted_boxes_chunk, axis=0)
        pos_x = split_projection_profile(x_projection, 0, 1)
        if not pos_x:
            continue

        arr_x0, arr_x1 = pos_x
        if len(arr_x0) == 1:
            # x-direction cannot be divided
            res.extend(x_sorted_indices_chunk)
            continue

        # can be separated in the x-direction and continue to call recursively
        for c0, c1 in zip(arr_x0, arr_x1):
            _indices = (c0 <= x_sorted_boxes_chunk[:, 0]) & (x_sorted_boxes_chunk[:, 0] < c1)
            recursive_xy_cut(
                x_sorted_boxes_chunk[_indices],
                x_sorted_indices_chunk[_indices],
                res,
            )


def recursive_xy_cut_swapped(boxes: np.ndarray, indices: np.ndarray, res: List[int]):
    """
    Args:
        boxes: (N, 4) - Numpy array representing bounding boxes with shape (N, 4)
        where each row is (left, top, right, bottom)
        indices: An array representing indices that correspond to boxes in the original data
        res: A list to save the output results
    """

    # Sort the bounding boxes based on x-coordinates (flipped)
    assert len(boxes) == len(indices)
    _indices = boxes[:, 0].argsort()
    x_sorted_boxes = boxes[_indices]
    x_sorted_indices = indices[_indices]

    # Project the boxes onto the x-axis and split the projection profile
    x_projection = projection_by_bboxes(boxes=x_sorted_boxes, axis=0)
    pos_x = split_projection_profile(x_projection, 0, 1)

    if not pos_x:
        return

    arr_x0, arr_x1 = pos_x

    # Loop over the segments obtained from the x-axis projection
    for c0, c1 in zip(arr_x0, arr_x1):
        # Obtain sub-boxes in the x-axis segment
        _indices = (c0 <= x_sorted_boxes[:, 0]) & (x_sorted_boxes[:, 0] < c1)
        x_sorted_boxes_chunk = x_sorted_boxes[_indices]
        x_sorted_indices_chunk = x_sorted_indices[_indices]

        # Sort the sub-boxes based on y-coordinates (flipped)
        _indices = x_sorted_boxes_chunk[:, 1].argsort()
        y_sorted_boxes_chunk = x_sorted_boxes_chunk[_indices]
        y_sorted_indices_chunk = x_sorted_indices_chunk[_indices]

        # Project the sub-boxes onto the y-axis and split the projection profile
        y_projection = projection_by_bboxes(boxes=y_sorted_boxes_chunk, axis=1)
        pos_y = split_projection_profile(y_projection, 0, 1)

        if not pos_y:
            continue

        arr_y0, arr_y1 = pos_y

        if len(arr_y0) == 1:
            # If there's no splitting along the y-axis, add the indices to the result
            res.extend(y_sorted_indices_chunk)
            continue

        # Recursive call for sub-boxes along the y-axis segments
        for r0, r1 in zip(arr_y0, arr_y1):
            _indices = (r0 <= y_sorted_boxes_chunk[:, 1]) & (y_sorted_boxes_chunk[:, 1] < r1)
            recursive_xy_cut_swapped(
                y_sorted_boxes_chunk[_indices],
                y_sorted_indices_chunk[_indices],
                res,
            )


def points_to_bbox(points):
    assert len(points) == 8

    # [x1,y1,x2,y2,x3,y3,x4,y4]
    left = min(points[::2])
    right = max(points[::2])
    top = min(points[1::2])
    bottom = max(points[1::2])

    left = max(left, 0)
    top = max(top, 0)
    right = max(right, 0)
    bottom = max(bottom, 0)
    return [left, top, right, bottom]


def bbox2points(bbox):
    left, top, right, bottom = bbox
    return [left, top, right, top, right, bottom, left, bottom]


@requires_dependencies("cv2")
def vis_polygon(img, points, thickness=2, color=None):
    import cv2

    br2bl_color = color
    tl2tr_color = color
    tr2br_color = color
    bl2tl_color = color
    cv2.line(
        img,
        (points[0][0], points[0][1]),
        (points[1][0], points[1][1]),
        color=tl2tr_color,
        thickness=thickness,
    )

    cv2.line(
        img,
        (points[1][0], points[1][1]),
        (points[2][0], points[2][1]),
        color=tr2br_color,
        thickness=thickness,
    )

    cv2.line(
        img,
        (points[2][0], points[2][1]),
        (points[3][0], points[3][1]),
        color=br2bl_color,
        thickness=thickness,
    )

    cv2.line(
        img,
        (points[3][0], points[3][1]),
        (points[0][0], points[0][1]),
        color=bl2tl_color,
        thickness=thickness,
    )
    return img


@requires_dependencies("cv2")
def vis_points(
    img: np.ndarray,
    points,
    texts: List[str],
    color=(0, 200, 0),
) -> np.ndarray:
    """

    Args:
        img:
        points: [N, 8]  8: x1,y1,x2,y2,x3,y3,x4,y4
        texts:
        color:

    Returns:

    """
    import cv2

    points = np.array(points)
    assert len(texts) == points.shape[0]

    for i, _points in enumerate(points):
        vis_polygon(img, _points.reshape(-1, 2), thickness=2, color=color)
        bbox = points_to_bbox(_points)
        left, top, right, bottom = bbox
        cx = (left + right) // 2
        cy = (top + bottom) // 2

        txt = texts[i]
        font = cv2.FONT_HERSHEY_SIMPLEX
        cat_size = cv2.getTextSize(txt, font, 0.5, 2)[0]

        img = cv2.rectangle(
            img,
            (cx - 5 * len(txt), cy - cat_size[1] - 5),
            (cx - 5 * len(txt) + cat_size[0], cy - 5),
            color,
            -1,
        )

        img = cv2.putText(
            img,
            txt,
            (cx - 5 * len(txt), cy - 5),
            font,
            0.5,
            (255, 255, 255),
            thickness=1,
            lineType=cv2.LINE_AA,
        )

    return img


def vis_polygons_with_index(image, points):
    texts = [str(i) for i in range(len(points))]
    res_img = vis_points(image.copy(), points, texts)
    return res_img
