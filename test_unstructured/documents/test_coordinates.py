import pytest

from unstructured.documents.coordinates import (
    CoordinateSystem,
    Orientation,
    RelativeCoordinateSystem,
    convert_coordinate,
)


@pytest.mark.parametrize(
    ("old_t", "old_t_max", "new_t_max", "t_orientation", "expected"),
    [(0, 7, 5, 1, 0), (7, 7, 5, 1, 5), (0, 7, 5, -1, 5), (7, 7, 5, -1, 0)],
)
def test_convert_coordinate(old_t, old_t_max, new_t_max, t_orientation, expected):
    assert convert_coordinate(old_t, old_t_max, new_t_max, t_orientation) == expected


@pytest.mark.parametrize(
    ("width", "height", "orientation", "x", "y", "expected_x", "expected_y"),
    [
        (100, 300, Orientation.CARTESIAN, 0.8, 0.4, 80, 120),
        (100, 300, Orientation.SCREEN, 0.8, 0.6, 80, 120),
    ],
)
def test_convert_from_relative(width, height, orientation, x, y, expected_x, expected_y):
    coord1 = CoordinateSystem(width, height)
    coord1.orientation = orientation
    assert coord1.convert_from_relative(x, y) == (expected_x, expected_y)


@pytest.mark.parametrize(
    ("width", "height", "orientation", "x", "y", "expected_x", "expected_y"),
    [
        (100, 300, Orientation.CARTESIAN, 80, 120, 0.8, 0.4),
        (100, 300, Orientation.SCREEN, 80, 120, 0.8, 0.6),
    ],
)
def test_convert_to_relative(width, height, orientation, x, y, expected_x, expected_y):
    coord1 = CoordinateSystem(width, height)
    coord1.orientation = orientation
    assert coord1.convert_to_relative(x, y) == (expected_x, expected_y)


@pytest.mark.parametrize(
    ("orientation1", "orientation2", "x", "y", "expected_x", "expected_y"),
    [
        (Orientation.CARTESIAN, Orientation.CARTESIAN, 80, 120, 800, 1200),
        (Orientation.CARTESIAN, Orientation.SCREEN, 80, 120, 800, 800),
        (Orientation.SCREEN, Orientation.CARTESIAN, 80, 120, 800, 800),
        (Orientation.SCREEN, Orientation.SCREEN, 80, 120, 800, 1200),
    ],
)
def test_convert_to_new_system(orientation1, orientation2, x, y, expected_x, expected_y):
    coord1 = CoordinateSystem(width=100, height=200)
    coord1.orientation = orientation1
    coord2 = CoordinateSystem(width=1000, height=2000)
    coord2.orientation = orientation2
    assert coord1.convert_coordinates_to_new_system(coord2, x, y) == (expected_x, expected_y)


@pytest.mark.parametrize(
    ("width", "height", "orientation", "x", "y", "expected_x", "expected_y"),
    [
        (100, 300, Orientation.CARTESIAN, 80, 120, 0.8, 0.4),
        (100, 300, Orientation.SCREEN, 80, 120, 0.8, 0.6),
    ],
)
def test_relative_system(width, height, orientation, x, y, expected_x, expected_y):
    coord1 = CoordinateSystem(width, height)
    coord1.orientation = orientation
    coord2 = RelativeCoordinateSystem()
    assert coord1.convert_coordinates_to_new_system(coord2, x, y) == (expected_x, expected_y)
