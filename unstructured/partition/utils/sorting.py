from typing import List

import numpy as np

from unstructured.documents.elements import CoordinatesMetadata, Element
from unstructured.logger import logger
from unstructured.partition.utils.constants import SORT_MODE_BASIC, SORT_MODE_XY_CUT
from unstructured.partition.utils.xycut import recursive_xy_cut


def coordinates_to_bbox(coordinates: CoordinatesMetadata) -> List[int]:
    points = coordinates.points
    left, top = points[0]
    right, bottom = points[2]
    return [int(left), int(top), int(right), int(bottom)]


def sort_page_elements(
    page_elements: List[Element],
    sort_mode: str = SORT_MODE_XY_CUT,
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

    if not page_elements:
        return []

    if sort_mode == SORT_MODE_XY_CUT:
        coordinates_list = [el.metadata.coordinates for el in page_elements]
        if any(coords is None for coords in coordinates_list):
            logger.warning(
                "some or all elements are missing coordinates from this page so we can't sort the "
                "elements",
            )
            sorted_page_elements = page_elements
        else:
            boxes = [coordinates_to_bbox(coords) for coords in coordinates_list]
            res: List[int] = []
            recursive_xy_cut(np.asarray(boxes).astype(int), np.arange(len(boxes)), res)
            sorted_page_elements = [page_elements[i] for i in res]
    elif sort_mode == SORT_MODE_BASIC:
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
