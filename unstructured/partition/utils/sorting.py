from typing import List

import numpy as np

from unstructured.documents.elements import CoordinatesMetadata, Element
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
):
    if sort_mode == SORT_MODE_XY_CUT:
        coordinates_list = [el.metadata.coordinates for el in page_elements]
        boxes = [coordinates_to_bbox(coords) for coords in coordinates_list]
        res = []
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
