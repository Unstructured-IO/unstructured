from functools import partial

import pytest

from unstructured.cleaners.core import clean_prefix
from unstructured.cleaners.translate import translate_text
from unstructured.documents.coordinates import (
    CoordinateSystem,
    Orientation,
    RelativeCoordinateSystem,
)
from unstructured.documents.elements import CoordinatesMetadata, Element, NoID, Text


def test_text_id():
    text_element = Text(text="hello there!")
    assert text_element.id == "c69509590d81db2f37f9d75480c8efed"


def test_element_defaults_to_blank_id():
    element = Element()
    assert isinstance(element.id, NoID)


def test_text_element_apply_cleaners():
    text_element = Text(text="[1] A Textbook on Crocodile Habitats")

    text_element.apply(partial(clean_prefix, pattern=r"\[\d{1,2}\]"))
    assert str(text_element) == "A Textbook on Crocodile Habitats"


def test_text_element_apply_multiple_cleaners():
    cleaners = [
        partial(clean_prefix, pattern=r"\[\d{1,2}\]"),
        partial(translate_text, target_lang="ru"),
    ]
    text_element = Text(text="[1] A Textbook on Crocodile Habitats")
    text_element.apply(*cleaners)
    assert str(text_element) == "Учебник по крокодильным средам обитания"


def test_apply_raises_if_func_does_not_produce_string():
    text_element = Text(text="[1] A Textbook on Crocodile Habitats")
    with pytest.raises(ValueError):
        text_element.apply(lambda s: 1)


@pytest.mark.parametrize(
    ("coordinates", "orientation1", "orientation2", "expected_coords"),
    [
        (
            ((1, 2), (1, 4), (3, 4), (3, 2)),
            Orientation.CARTESIAN,
            Orientation.CARTESIAN,
            ((10, 20), (10, 40), (30, 40), (30, 20)),
        ),
        (
            ((1, 2), (1, 4), (3, 4), (3, 2)),
            Orientation.CARTESIAN,
            Orientation.SCREEN,
            ((10, 1980), (10, 1960), (30, 1960), (30, 1980)),
        ),
        (
            ((1, 2), (1, 4), (3, 4), (3, 2)),
            Orientation.SCREEN,
            Orientation.CARTESIAN,
            ((10, 1980), (10, 1960), (30, 1960), (30, 1980)),
        ),
        (
            ((1, 2), (1, 4), (3, 4), (3, 2)),
            Orientation.SCREEN,
            Orientation.SCREEN,
            ((10, 20), (10, 40), (30, 40), (30, 20)),
        ),
    ],
)
def test_convert_coordinates_to_new_system(
    coordinates,
    orientation1,
    orientation2,
    expected_coords,
):
    coord1 = CoordinateSystem(100, 200)
    coord1.orientation = orientation1
    coord2 = CoordinateSystem(1000, 2000)
    coord2.orientation = orientation2
    element = Element(coordinates=coordinates, coordinate_system=coord1)
    new_coords = element.convert_coordinates_to_new_system(coord2)
    for new_coord, expected_coord in zip(new_coords, expected_coords):
        new_coord == pytest.approx(expected_coord)
    element.convert_coordinates_to_new_system(coord2, in_place=True)
    for new_coord, expected_coord in zip(element.metadata.coordinates.points, expected_coords):
        assert new_coord == pytest.approx(expected_coord)
    assert element.metadata.coordinates.system == coord2


def test_convert_coordinate_to_new_system_none():
    element = Element(coordinates=None, coordinate_system=None)
    coord = CoordinateSystem(100, 200)
    coord.orientation = Orientation.SCREEN
    assert element.convert_coordinates_to_new_system(coord) is None


def test_element_constructor_coordinates_all_present():
    coordinates = ((1, 2), (1, 4), (3, 4), (3, 2))
    coordinate_system = RelativeCoordinateSystem()
    element = Element(coordinates=coordinates, coordinate_system=coordinate_system)
    expected_coordinates_metadata = CoordinatesMetadata(
        points=coordinates,
        system=coordinate_system,
    )
    assert element.metadata.coordinates == expected_coordinates_metadata


def test_element_constructor_coordinates_points_absent():
    with pytest.raises(ValueError) as exc_info:
        Element(coordinate_system=RelativeCoordinateSystem())
    assert (
        str(exc_info.value)
        == "Coordinates points should not exist without coordinates system and vice versa."
    )


def test_element_constructor_coordinates_system_absent():
    with pytest.raises(ValueError) as exc_info:
        Element(coordinates=((1, 2), (1, 4), (3, 4), (3, 2)))
    assert (
        str(exc_info.value)
        == "Coordinates points should not exist without coordinates system and vice versa."
    )


def test_coordinate_metadata_serdes():
    coordinates = ((1, 2), (1, 4), (3, 4), (3, 2))
    coordinate_system = RelativeCoordinateSystem()
    coordinates_metadata = CoordinatesMetadata(points=coordinates, system=coordinate_system)
    expected_schema = {
        "layout_height": 1,
        "layout_width": 1,
        "points": ((1, 2), (1, 4), (3, 4), (3, 2)),
        "system": "RelativeCoordinateSystem",
    }
    coordinates_metadata_dict = coordinates_metadata.to_dict()
    assert coordinates_metadata_dict == expected_schema
    assert CoordinatesMetadata.from_dict(coordinates_metadata_dict) == coordinates_metadata


def test_element_to_dict():
    coordinates = ((1, 2), (1, 4), (3, 4), (3, 2))
    coordinate_system = RelativeCoordinateSystem()
    element = Element(
        element_id="awt32t1",
        coordinates=coordinates,
        coordinate_system=coordinate_system,
    )
    expected = {
        "metadata": {
            "coordinates": {
                "layout_height": 1,
                "layout_width": 1,
                "points": ((1, 2), (1, 4), (3, 4), (3, 2)),
                "system": "RelativeCoordinateSystem",
            },
        },
        "type": None,
        "element_id": "awt32t1",
    }
    assert element.to_dict() == expected
