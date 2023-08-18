from typing import List

import numpy as np

from unstructured.documents.elements import Element, PageBreak
from unstructured.partition.utils.xycut import recursive_xy_cut


def extract_element_coordinates(elements):
    elements_coordinates = []
    page_elements_coordinates = []

    for el in elements:
        if isinstance(el, PageBreak):
            if page_elements_coordinates:
                elements_coordinates.append(page_elements_coordinates)
                page_elements_coordinates = []
        else:
            page_elements_coordinates.append(el.metadata.coordinates)

    if page_elements_coordinates:
        elements_coordinates.append(page_elements_coordinates)

    return elements_coordinates


def convert_coordinates_to_boxes(coordinates):
    boxes = []

    for coordinate in coordinates:
        points = coordinate.points
        left, top = points[0]
        right, bottom = points[2]
        boxes.append([int(left), int(top), int(right), int(bottom)])

    return boxes


def order_elements(elements: List[Element]) -> List[Element]:
    elements_coordinates = [el.metadata.coordinates for el in elements]
    boxes = convert_coordinates_to_boxes(elements_coordinates)
    res = []

    recursive_xy_cut(np.asarray(boxes).astype(int), np.arange(len(boxes)), res)

    ordered_elements = [elements[i] for i in res]
    return ordered_elements
