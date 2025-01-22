import numpy as np
import pytest
from unstructured_inference.inference.elements import TextRegions

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import CoordinatesMetadata, Element, Text
from unstructured.partition.utils.constants import SORT_MODE_BASIC, SORT_MODE_XY_CUT
from unstructured.partition.utils.sorting import (
    coord_has_valid_points,
    coordinates_to_bbox,
    shrink_bbox,
    sort_page_elements,
    sort_text_regions,
)


class MockCoordinatesMetadata(CoordinatesMetadata):
    def __init__(self, points):
        system = PixelSpace(width=300, height=500)

        super().__init__(points, system)


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


def test_sort_text_regions():
    unsorted = TextRegions(
        element_coords=np.array(
            [[1, 2, 2, 2], [1, 1, 2, 2], [3, 1, 4, 4]],
        ),
        texts=np.array(["1", "2", "3"]),
        sources=np.array(["foo"] * 3),
    )
    assert sort_text_regions(unsorted, sort_mode=SORT_MODE_BASIC).texts.tolist() == ["2", "3", "1"]


@pytest.mark.parametrize(
    "coords",
    [
        [[1, 2, 2, 2], [1, 1, 2, 2], [3, -1, 4, 4]],
        [[1, 2, 2, 2], [1, 1, 2, 2], [3, None, 4, 4]],
    ],
)
def test_sort_text_regions_with_invalid_coords_using_xy_cut_does_no_ops(coords):
    unsorted = TextRegions(
        element_coords=np.array(coords).astype(float),
        texts=np.array(["1", "2", "3"]),
        sources=np.array(["foo"] * 3),
    )
    assert sort_text_regions(unsorted).texts.tolist() == ["1", "2", "3"]


def test_coordinates_to_bbox():
    coordinates_data = MockCoordinatesMetadata([(10, 20), (10, 200), (100, 200), (100, 20)])
    expected_result = (10, 20, 100, 200)
    assert coordinates_to_bbox(coordinates_data) == expected_result


def test_shrink_bbox():
    bbox = (0, 0, 200, 100)
    shrink_factor = 0.9
    expected_result = (0, 0, 180, 90)
    assert shrink_bbox(bbox, shrink_factor) == expected_result

    bbox = (20, 20, 320, 120)
    shrink_factor = 0.9
    expected_result = (20, 20, 290, 110)
    assert shrink_bbox(bbox, shrink_factor) == expected_result
