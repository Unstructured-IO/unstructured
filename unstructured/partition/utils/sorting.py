from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, List

import numpy as np

from unstructured.documents.elements import CoordinatesMetadata, Element
from unstructured.logger import trace_logger
from unstructured.partition.utils.constants import SORT_MODE_BASIC, SORT_MODE_XY_CUT
from unstructured.partition.utils.xycut import recursive_xy_cut, recursive_xy_cut_swapped

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegions


def coordinates_to_bbox(coordinates: CoordinatesMetadata) -> tuple[int, int, int, int]:
    """
    Convert coordinates to a bounding box representation.

    Parameters:
        coordinates (CoordinatesMetadata): Metadata containing points to represent the bounding box.

    Returns:
        tuple[int, int, int, int]: A tuple representing the bounding box in the format
        (left, top, right, bottom).
    """

    points = coordinates.points
    left, top = points[0]
    right, bottom = points[2]
    return int(left), int(top), int(right), int(bottom)


def shrink_bbox(bbox: tuple[int, int, int, int], shrink_factor) -> tuple[int, int, int, int]:
    """
    Shrink a bounding box by a given shrink factor while maintaining its top and left.
    """
    left, top, right, bottom = bbox
    width = right - left
    height = bottom - top
    new_width = width * shrink_factor
    new_height = height * shrink_factor
    dw = width - new_width
    dh = height - new_height

    new_right = right - dw
    new_bottom = bottom - dh
    return int(left), int(top), int(new_right), int(new_bottom)


def coord_has_valid_points(coordinates: CoordinatesMetadata) -> bool:
    """
    Verifies all 4 points in a coordinate exist and are positive.
    """
    if not coordinates:
        return False
    if len(coordinates.points) != 4:
        return False
    for point in coordinates.points:
        if len(point) != 2:
            return False
        try:
            if point[0] < 0 or point[1] < 0:
                return False
        except TypeError:
            return False
    return True


def bbox_is_valid(bbox: Any) -> bool:
    """
    Verifies all 4 values in a bounding box exist and are positive.
    """
    if not bbox:
        return False
    if len(bbox) != 4:
        return False
    for v in bbox:
        try:
            if v < 0:
                return False
        except TypeError:
            return False
    return True


def sort_page_elements(
    page_elements: list[Element],
    sort_mode: str = SORT_MODE_XY_CUT,
    shrink_factor: float = 0.9,
    xy_cut_primary_direction: str = "x",
) -> list[Element]:
    """
    Sorts a list of page elements based on the specified sorting mode.
    """
    shrink_factor = float(
        os.environ.get("UNSTRUCTURED_XY_CUT_BBOX_SHRINK_FACTOR", shrink_factor),
    )

    xy_cut_primary_direction = os.environ.get(
        "UNSTRUCTURED_XY_CUT_PRIMARY_DIRECTION",
        xy_cut_primary_direction,
    )

    if not page_elements:
        return []

    # --- ACADEMIC FIX START ---
    # Force column-aware sorting if elements are dense (Academic papers)
    if sort_mode == "COORDINATE_COLUMNS" or len(page_elements) > 80:
        return sort_page_elements_columns(page_elements)
    # --- ACADEMIC FIX END ---

    coordinates_list = [el.metadata.coordinates for el in page_elements]

    def _coords_ok(strict_points: bool):
        warned = False
        for coord in coordinates_list:
            if coord is None or not coord.points:
                trace_logger.detail("some or all elements are missing coordinates, skipping sort")
                return False
            elif not coord_has_valid_points(coord):
                if not warned:
                    trace_logger.detail(f"coord {coord} does not have valid points")
                    warned = True
                if strict_points:
                    return False
        return True

    if sort_mode == SORT_MODE_XY_CUT:
        if not _coords_ok(strict_points=True):
            return page_elements
        shrunken_bboxes = []
        for coords in coordinates_list:
            bbox = coordinates_to_bbox(coords)
            shrunken_bbox = shrink_bbox(bbox, shrink_factor)
            shrunken_bboxes.append(shrunken_bbox)

        res: list[int] = []
        xy_cut_sorting_func = (
            recursive_xy_cut_swapped if xy_cut_primary_direction == "x" else recursive_xy_cut
        )
        xy_cut_sorting_func(
            np.asarray(shrunken_bboxes).astype(int),
            np.arange(len(shrunken_bboxes)),
            res,
        )
        sorted_page_elements = [page_elements[i] for i in res]
    elif sort_mode == SORT_MODE_BASIC:
        if not _coords_ok(strict_points=False):
            return page_elements
        sorted_page_elements = sorted(
            page_elements,
            key=lambda el: (
                el.metadata.coordinates.points[0][1] if el.metadata.coordinates else float("inf"),
                el.metadata.coordinates.points[0][0] if el.metadata.coordinates else float("inf"),
            ),
        )
    else:
        sorted_page_elements = page_elements

    return sorted_page_elements


def sort_page_elements_columns(page_elements: list[Element]) -> list[Element]:
    """
    Handles academic double-column sorting by binning into Top, Left-Col, Right-Col, and Bottom zones.
    """
    if not page_elements:
        return []

    all_coords = [el.metadata.coordinates.points for el in page_elements if el.metadata.coordinates]
    if not all_coords:
        return page_elements
        
    max_x = max([p[2][0] for p in all_coords])
    max_y = max([p[2][1] for p in all_coords])
    mid_x = max_x / 2

    top_block, left_col, right_col, bottom_block = [], [], [], []

    for el in page_elements:
        if not el.metadata.coordinates:
            top_block.append(el)
            continue

        x_start, y_start = el.metadata.coordinates.points[0]
        x_end, y_end = el.metadata.coordinates.points[2]
        
        # Logic: Separating Footer, Header, and Two Columns
        if y_start > (max_y * 0.92):
            bottom_block.append(el)
        elif (x_end - x_start) > (max_x * 0.65) or y_start < (max_y * 0.12):
            top_block.append(el)
        elif x_start < mid_x:
            left_col.append(el)
        else:
            right_col.append(el)

    y_sort = lambda e: e.metadata.coordinates.points[0][1] if e.metadata.coordinates else 0
    top_block.sort(key=y_sort)
    left_col.sort(key=y_sort)
    right_col.sort(key=y_sort)
    bottom_block.sort(key=y_sort)

    return top_block + left_col + right_col + bottom_block


def sort_bboxes_by_xy_cut(
    bboxes,
    shrink_factor: float = 0.9,
    xy_cut_primary_direction: str = "x",
):
    """Sort bounding boxes using XY-cut algorithm."""
    shrunken_bboxes = []
    for bbox in bboxes:
        shrunken_bbox = shrink_bbox(bbox, shrink_factor)
        shrunken_bboxes.append(shrunken_bbox)

    res: list[int] = []
    xy_cut_sorting_func = (
        recursive_xy_cut_swapped if xy_cut_primary_direction == "x" else recursive_xy_cut
    )
    xy_cut_sorting_func(
        np.asarray(shrunken_bboxes).astype(int),
        np.arange(len(shrunken_bboxes)),
        res,
    )
    return res


def sort_text_regions(
    elements: TextRegions,
    sort_mode: str = SORT_MODE_XY_CUT,
    shrink_factor: float = 0.9,
    xy_cut_primary_direction: str = "x",
) -> TextRegions:
    """Sort a list of TextRegion elements based on the specified sorting mode."""
    if not elements:
        return elements

    bboxes = elements.element_coords

    if sort_mode == SORT_MODE_XY_CUT:
        if np.isnan(bboxes).any():
            return elements
        res = sort_bboxes_by_xy_cut(
            bboxes=bboxes,
            shrink_factor=shrink_factor,
            xy_cut_primary_direction=xy_cut_primary_direction,
        )
        sorted_elements = elements.slice(res)
    elif sort_mode == SORT_MODE_BASIC:
        sorted_elements = elements.slice(
            np.lexsort((elements.x2, elements.y2, elements.x1, elements.y1))
        )
    else:
        sorted_elements = elements

    return sorted_elements