import numpy as np
import pytest
from unstructured_inference.inference.elements import TextRegions

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import CoordinatesMetadata, Text
from unstructured.partition.utils.sorting import (
    coord_has_valid_points,
    sort_page_elements,
    sort_text_regions,
)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_coordinate_validation_rejects_nonfinite_points(value):
    coordinates = CoordinatesMetadata(
        [(10, 10), (10, 30), (30, value), (30, 10)], PixelSpace(100, 100)
    )

    assert coord_has_valid_points(coordinates) is False


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_xycut_preserves_page_elements_with_nonfinite_coordinates(value):
    elements = [Text("first"), Text("second")]
    elements[0].metadata.coordinates = CoordinatesMetadata(
        [(10, 50), (10, 70), (30, 70), (30, 50)], PixelSpace(100, 100)
    )
    elements[1].metadata.coordinates = CoordinatesMetadata(
        [(10, 10), (10, 30), (value, 30), (30, 10)], PixelSpace(100, 100)
    )

    result = sort_page_elements(elements)

    assert result is elements
    assert [element.text for element in result] == ["first", "second"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_xycut_preserves_text_regions_with_nonfinite_bounds(value):
    coords = np.array([[10, 50, 30, 70], [10, 10, value, 30]], dtype=float)
    regions = TextRegions(
        element_coords=coords.copy(),
        texts=np.array(["first", "second"]),
        sources=np.array(["ocr", "ocr"]),
    )

    result = sort_text_regions(regions)

    assert result is regions
    assert result.texts.tolist() == ["first", "second"]
    np.testing.assert_array_equal(result.element_coords, coords)


def test_xycut_still_sorts_finite_bounds():
    regions = TextRegions(
        element_coords=np.array([[10, 50, 30, 70], [10, 10, 30, 30]], dtype=float),
        texts=np.array(["second", "first"]),
        sources=np.array(["ocr", "ocr"]),
    )

    assert sort_text_regions(regions).texts.tolist() == ["first", "second"]
