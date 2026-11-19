"""COCO boxes use top-left coordinates and bounds independent of polygon order."""

from copy import deepcopy

import pytest

from unstructured.documents.coordinates import PixelSpace, PointSpace
from unstructured.documents.elements import Text
from unstructured.staging.base import convert_to_coco


@pytest.mark.parametrize("system_type", [PixelSpace, PointSpace])
@pytest.mark.parametrize("order", [(0, 1, 2, 3), (3, 2, 1, 0), (1, 2, 3, 0), (0, 3, 2, 1)])
def test_rectangle_box_is_independent_of_order_and_orientation(system_type, order):
    screen_points = ((10, 20), (10, 60), (30, 60), (30, 20))
    points = tuple(
        (screen_points[index][0], 200 - screen_points[index][1])
        if system_type is PointSpace
        else screen_points[index]
        for index in order
    )
    element = Text("rectangle", coordinates=points, coordinate_system=system_type(100, 200))
    before = deepcopy(element.metadata.to_dict())

    result = convert_to_coco([element])

    assert result["annotations"][0]["bbox"] == pytest.approx([10, 20, 20, 40])
    assert result["annotations"][0]["area"] == pytest.approx(800)
    assert result["images"][0]["width"] == 100
    assert result["images"][0]["height"] == 200
    assert element.metadata.to_dict() == before


@pytest.mark.parametrize(
    ("points", "expected"),
    [
        (((10, 20), (40, 20), (25, 70)), [10, 20, 30, 50]),
        (((25, 10), (40, 30), (25, 50), (10, 30)), [10, 10, 30, 40]),
        (((30, 60), (10, 20)), [10, 20, 20, 40]),
    ],
)
def test_polygon_bounds_use_all_vertices(points, expected):
    element = Text("polygon", coordinates=points, coordinate_system=PixelSpace(100, 200))

    annotation = convert_to_coco([element])["annotations"][0]

    assert annotation["bbox"] == pytest.approx(expected)
    assert annotation["area"] == pytest.approx(expected[2] * expected[3])


def test_missing_coordinates_keep_the_existing_empty_geometry():
    annotation = convert_to_coco([Text("no location")])["annotations"][0]

    assert annotation["bbox"] == []
    assert annotation["area"] is None


def test_cartesian_export_has_unit_iou_with_the_same_screen_rectangle():
    mask = pytest.importorskip("pycocotools.mask")
    element = Text(
        "rectangle",
        coordinates=((10, 180), (30, 180), (30, 140), (10, 140)),
        coordinate_system=PointSpace(100, 200),
    )

    box = convert_to_coco([element])["annotations"][0]["bbox"]

    assert mask.iou([box], [[10, 20, 20, 40]], [0])[0, 0] == pytest.approx(1)
