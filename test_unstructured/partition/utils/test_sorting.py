import pytest

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import CoordinatesMetadata, Element, Text
from unstructured.partition.utils.constants import SORT_MODE_BASIC, SORT_MODE_XY_CUT
from unstructured.partition.utils.sorting import (
    coord_has_valid_points,
    sort_page_elements,
)


def test_coord_valid_coordinates():
    coordinates = CoordinatesMetadata([(1, 2), (3, 4), (5, 6), (7, 8)], PixelSpace)
    assert coord_has_valid_points(coordinates) is True


def test_coord_missing_incomplete_point():
    coordinates = CoordinatesMetadata([(1, 2), (3, 4), (5, 6)], PixelSpace)
    assert coord_has_valid_points(coordinates) is False


def test_coord_negative_values():
    coordinates = CoordinatesMetadata([(1, 2), (3, 4), (5, -6), (7, 8)], PixelSpace)
    assert coord_has_valid_points(coordinates) is False


def test_coord_weird_values():
    coordinates = CoordinatesMetadata([(1, 2), ("3", 4), (5, 6), (7, 8)], PixelSpace)
    assert coord_has_valid_points(coordinates) is False


def test_coord_invalid_point_structure():
    coordinates = CoordinatesMetadata([(1, 2), (3, 4, 5), (6, 7), (8, 9)], PixelSpace)
    assert coord_has_valid_points(coordinates) is False


@pytest.mark.parametrize("sort_mode", ["xy-cut", "basic"])
def test_sort_page_elements_without_coordinates(sort_mode):
    elements = [Element(str(idx)) for idx in range(5)]
    assert sort_page_elements(elements) == elements


def test_sort_xycut_neg_coordinates():
    elements = []
    for idx in range(2):
        elem = Text(str(idx))
        elem.metadata.coordinates = CoordinatesMetadata(
            [(0, idx), (3, 4), (6, 7), (8, 9)],
            PixelSpace,
        )
        elements.append(elem)

    # NOTE(crag): xycut not attempted, sort_page_elements returns original list
    assert sort_page_elements(elements, sort_mode=SORT_MODE_XY_CUT) is not elements


def test_sort_xycut_pos_coordinates():
    elements = []
    for idx in range(2):
        elem = Text(str(idx))
        elem.metadata.coordinates = CoordinatesMetadata(
            [(1, 2), (3, 4), (6, 7), (8, 9)],
            PixelSpace,
        )
        elements.append(elem)

    # NOTE(crag): xycut ran, so different list reference returned from input list
    assert sort_page_elements(elements, sort_mode=SORT_MODE_XY_CUT) is not elements


def test_sort_basic_neg_coordinates():
    elements = []
    for idx in range(3):
        elem = Text(str(idx))
        elem.metadata.coordinates = CoordinatesMetadata(
            [(1, -idx), (3, 4), (6, 7), (8, 9)],
            PixelSpace,
        )
        elements.append(elem)

    sorted_page_elements = sort_page_elements(elements, sort_mode=SORT_MODE_BASIC)
    sorted_elem_text = " ".join([str(elem.text) for elem in sorted_page_elements])
    assert sorted_elem_text == "2 1 0"


def test_sort_basic_pos_coordinates():
    elements = []
    for idx in range(3):
        elem = Text(str(9 - idx))
        elem.metadata.coordinates = CoordinatesMetadata(
            [(1, 9 - idx), (3, 4), (6, 7), (8, 9)],
            PixelSpace,
        )
        elements.append(elem)

    sorted_page_elements = sort_page_elements(elements, sort_mode=SORT_MODE_BASIC)
    assert sorted_page_elements is not elements

    sorted_elem_text = " ".join([str(elem.text) for elem in sorted_page_elements])
    assert sorted_elem_text == "7 8 9"
