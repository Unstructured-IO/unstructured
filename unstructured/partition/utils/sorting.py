import os
from typing import TYPE_CHECKING, Any, List, Tuple

import numpy as np

from unstructured.documents.elements import CoordinatesMetadata, Element
from unstructured.logger import trace_logger
from unstructured.partition.utils.constants import SORT_MODE_BASIC, SORT_MODE_XY_CUT
from unstructured.partition.utils.xycut import recursive_xy_cut, recursive_xy_cut_swapped

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegion


def coordinates_to_bbox(coordinates: CoordinatesMetadata) -> Tuple[int, int, int, int]:
    """
    Convert coordinates to a bounding box representation.

    Parameters:
        coordinates (CoordinatesMetadata): Metadata containing points to represent the bounding box.

    Returns:
        Tuple[int, int, int, int]: A tuple representing the bounding box in the format
        (left, top, right, bottom).
    """

    points = coordinates.points
    left, top = points[0]
    right, bottom = points[2]
    return int(left), int(top), int(right), int(bottom)


def shrink_bbox(bbox: Tuple[int, int, int, int], shrink_factor) -> Tuple[int, int, int, int]:
    """
    Shrink a bounding box by a given shrink factor while maintaining its top and left.

    Parameters:
        bbox (Tuple[int, int, int, int]): The original bounding box represented by
        (left, top, right, bottom).
        shrink_factor (float): The factor by which to shrink the bounding box (0.0 to 1.0).

    Returns:
        Tuple[int, int, int, int]: The shrunken bounding box represented by
        (left, top, right, bottom).
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
    page_elements: List[Element],
    sort_mode: str = SORT_MODE_XY_CUT,
    shrink_factor: float = 0.9,
    xy_cut_primary_direction: str = "x",
) -> List[Element]:
    """
    Sorts a list of page elements based on the specified sorting mode.

    Parameters:
    - page_elements (List[Element]): A list of elements representing parts of a page. Each element
     should have metadata containing coordinates.
    - sort_mode (str, optional): The mode by which the elements will be sorted. Default is
     SORT_MODE_XY_CUT.
        - SORT_MODE_XY_CUT: Sorts elements based on XY-cut sorting approach. Requires the
         recursive_xy_cut function and coordinates_to_bbox function to be defined. And requires all
         elements to have valid cooridnates
        - SORT_MODE_BASIC: Sorts elements based on their coordinates. Elements without coordinates
         will be pushed to the end.
        - If an unrecognized sort_mode is provided, the function returns the elements as-is.

    Returns:
    - List[Element]: A list of sorted page elements.
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

    coordinates_list = [el.metadata.coordinates for el in page_elements]

    def _coords_ok(strict_points: bool):
        warned = False

        for coord in coordinates_list:
            if coord is None or not coord.points:
                trace_logger.detail(  # type: ignore
                    "some or all elements are missing coordinates, skipping sort",
                )
                return False
            elif not coord_has_valid_points(coord):
                if not warned:
                    trace_logger.detail(f"coord {coord} does not have valid points")  # type: ignore
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

        res: List[int] = []
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
                el.id,
            ),
        )
    else:
        sorted_page_elements = page_elements

    return sorted_page_elements


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

    res: List[int] = []
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
    elements: List["TextRegion"],
    sort_mode: str = SORT_MODE_XY_CUT,
    shrink_factor: float = 0.9,
    xy_cut_primary_direction: str = "x",
) -> List["TextRegion"]:
    """Sort a list of TextRegion elements based on the specified sorting mode."""

    if not elements:
        return elements

    bboxes = [(el.bbox.x1, el.bbox.y1, el.bbox.x2, el.bbox.y2) for el in elements]

    def _bboxes_ok(strict_points: bool):
        warned = False

        for bbox in bboxes:
            if bbox is None:
                trace_logger.detail(  # type: ignore
                    "some or all elements are missing bboxes, skipping sort",
                )
                return False
            elif not bbox_is_valid(bbox):
                if not warned:
                    trace_logger.detail(f"bbox {bbox} does not have valid values")  # type: ignore
                    warned = True
                if strict_points:
                    return False
        return True

    if sort_mode == SORT_MODE_XY_CUT:
        if not _bboxes_ok(strict_points=True):
            return elements

        shrink_factor = float(
            os.environ.get("UNSTRUCTURED_XY_CUT_BBOX_SHRINK_FACTOR", shrink_factor),
        )

        xy_cut_primary_direction = os.environ.get(
            "UNSTRUCTURED_XY_CUT_PRIMARY_DIRECTION",
            xy_cut_primary_direction,
        )

        res = sort_bboxes_by_xy_cut(
            bboxes=bboxes,
            shrink_factor=shrink_factor,
            xy_cut_primary_direction=xy_cut_primary_direction,
        )
        sorted_elements = [elements[i] for i in res]
    else:
        sorted_elements = elements

    return sorted_elements
