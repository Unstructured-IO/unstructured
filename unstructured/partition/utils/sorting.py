from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

from unstructured.documents.elements import CoordinatesMetadata, Element
from unstructured.logger import trace_logger
from unstructured.partition.utils.constants import SORT_MODE_BASIC, SORT_MODE_DONT, SORT_MODE_XY_CUT
from unstructured.partition.utils.xycut import recursive_xy_cut, recursive_xy_cut_swapped

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegion, TextRegions


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

    Parameters:
        bbox (tuple[int, int, int, int]): The original bounding box represented by
        (left, top, right, bottom).
        shrink_factor (float): The factor by which to shrink the bounding box (0.0 to 1.0).

    Returns:
        tuple[int, int, int, int]: The shrunken bounding box represented by
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
    page_elements: list[Element],
    sort_mode: str = SORT_MODE_XY_CUT,
    shrink_factor: float = 0.9,
    xy_cut_primary_direction: str = "x",
) -> list[Element]:
    """
    Sorts a list of page elements based on the specified sorting mode.

    Parameters:
    - page_elements (list[Element]): A list of elements representing parts of a page. Each element
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
    - list[Element]: A list of sorted page elements.
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


def sort_document_elements_by_page(
    pages: list[list[Element]], sort_mode: str
) -> list[list[Element]]:
    """Sort a list of document elements while respecting page boundaries."""

    elements: list[list[Element]] = []
    for page_elements in pages:
        sorted_page_elements = (
            page_elements
            if sort_mode == SORT_MODE_DONT
            else sort_page_elements(page_elements, sort_mode=sort_mode)
        )
        elements.append(sorted_page_elements)

    return elements


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


def sort_bboxes_by_xy_cut_plus_plus(
    bboxes: Sequence[Element], document_median_width: float, scaling_factor: float = 1.3
):
    """Sort bounding boxes using XY-cut-plus-plus algorithm."""

    threshold_width = document_median_width * scaling_factor
    shrunken_bboxes = []
    for bbox in bboxes:
        shrunken_bbox = shrink_bbox(bbox, shrink_factor)
        shrunken_bboxes.append(shrunken_bbox)


def find_cross_layout_elements(text_regions: TextRegions, threshold_width: float) -> list[Element]:
    """Check if a bounding box is a cross-layout element. Returns a boolean mask selecting the cross
    layout elements"""
    textregion_widths = get_el_widths(text_regions)
    return (textregion_widths > threshold_width) & (
        elements_horizontally_overlap(text_regions=text_regions).sum(axis=-1) > 2
    )


def get_textregion_widths(text_regions: TextRegions) -> np.ndarray:
    """Get the widths of the elements in a TextRegions object."""
    return text_regions.element_coords[:, 2] - text_regions.element_coords[:, 0]


def textregions_horizontally_overlap(text_regions: TextRegions) -> np.ndarray:
    """Check if elements horizontally overlap."""
    x_0s = text_regions.element_coords[:, [0]]
    x_1s = text_regions.element_coords[:, [2]]
    return (x_0s < x_1s.T) & (x_1s > x_0s.T)


def textregions_vertically_overlap(text_regions: TextRegions) -> np.ndarray:
    """Check if elements vertically overlap."""
    y_0s = text_regions.element_coords[:, [1]]
    y_1s = text_regions.element_coords[:, [3]]
    return (y_0s < y_1s.T) & (y_1s > y_0s.T)


def textregions_overlap(text_regions: TextRegions) -> np.ndarray:
    """Check if elements overlap."""
    return textregions_vertically_overlap(text_regions) & textregions_horizontally_overlap(
        text_regions
    )


def get_textregion_centers(text_regions: TextRegions) -> np.array:
    xs = text_regions.element_coords[:, [0, 2]].mean(axis=-1)
    ys = text_regions.element_coords[:, [1, 3]].mean(axis=-1)
    return np.column_stack((xs, ys))


def get_central_text_regions(
    text_regions: TextRegions, page_center: np.ndarray, page_distance: float, threshold: float
) -> TextRegions:
    """
    Geometric presegmentation of text regions.
    """
    textregion_centers = get_textregion_centers(text_regions)
    distances_to_page_center = np.linalg.norm(textregion_centers - page_center, axis=-1)
    return text_regions.slice(distances_to_page_center / page_distance < threshold)


def get_textregion_distances(textregions: TextRegions) -> np.ndarray:
    x_overlaps = textregions_horizontally_overlap(textregions)
    y_overlaps = textregions_vertically_overlap(textregions)
    overlaps = x_overlaps & y_overlaps
    x_diffs = textregions[:, [0]] - textregions[:, [2]].T
    y_diffs = textregions[:, [1]] - textregions[:, [3]].T
    x_distances = np.stack([x_diffs, x_diffs.T], axis=-1).max(axis=-1).clip(0)
    y_distances = np.stack([y_diffs, y_diffs.T], axis=-1).max(axis=-1).clip(0)
    return np.linalg.norm(np.stack([x_distances, y_distances], axis=-1), axis=-1)


def get_distances_to_nearest_non_overlapping_bounding_box(textregions: TextRegions) -> np.ndarray:
    """
    Find the nearest non-overlapping bounding box.
    """
    # Take the difference between each bounding box's left x-coordinate and the right x-coordinate
    # of all other bounding boxes. When this difference is positive, that indicates a horizontal
    # separation between the two bounding boxes. Do the same for the y-coordinates.
    x_diffs = textregions.element_coords[:, [0]] - textregions.element_coords[:, [2]].T
    y_diffs = textregions.element_coords[:, [1]] - textregions.element_coords[:, [3]].T
    # For each pair A, B of bounding boxes, at most one of the above pairwise differences is
    # positive. We capture this by taking the maximum of the two differences, and cull the negative
    # values by clipping at 0.0.
    x_distances = np.stack([x_diffs, x_diffs.T], axis=-1).max(axis=-1).clip(0.0)
    y_distances = np.stack([y_diffs, y_diffs.T], axis=-1).max(axis=-1).clip(0.0)
    # We now find the distance between the closest points in pairs of bounding boxes. By taking the
    # norm of the x and y distances. This works because a distance of 0.0 for an axis indicates
    # overlap or adjacency on the axis, in which case the distance is the distance in the other axis
    # (exactly what the Euclidean norm in 2d gives when one coordinate is zero and the other is
    # positive). If both distances are positive, then the distance between the bounding boxes is
    # exactly the distance between the closest corners of the bounding boxes, which is exactly the
    # Euclidean norm of the horizontal and vertical separations.
    distances = np.linalg.norm(np.stack([x_distances, y_distances], axis=-1), axis=-1)
    # If the distance is 0.0, that means the bounding boxes are overlapping or adjacent, so we
    # set the distance to infinity as a way of 'disqualifying' the bounding box.
    # We then take the minimum of the distances from each bounding box to the others to get the
    # distance to the 'nearest non-overlapping (or adjacent) bounding box'.
    return np.where(distances == 0.0, np.inf, distances).min(axis=-1)


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

    def _bboxes_ok(strict_points: bool):

        if np.isnan(bboxes).any():
            trace_logger.detail(  # type: ignore
                "some or all elements are missing bboxes, skipping sort",
            )
            return False

        if bboxes.shape[1] != 4 or np.where(bboxes < 0)[0].size:
            trace_logger.detail("at least one bbox contains invalid values")  # type: ignore
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
        sorted_elements = elements.slice(res)
    elif sort_mode == SORT_MODE_BASIC:
        # NOTE (yao): lexsort order is revese from the input sequence; so below is first sort by y1,
        # then x1, then y2, lastly x2
        sorted_elements = elements.slice(
            np.lexsort((elements.x2, elements.y2, elements.x1, elements.y1))
        )
    else:
        sorted_elements = elements

    return sorted_elements


def median_bounding_box_width(elements: TextRegions) -> float:
    """
    Calculate the median bounding box width of a list of TextRegion elements.
    """
    return float(np.median(elements.element_coords[:, 2] - elements.element_coords[:, 0]))
