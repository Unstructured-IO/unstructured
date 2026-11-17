import pytest

from unstructured.documents.coordinates import PixelSpace, PointSpace, RelativeCoordinateSystem
from unstructured.documents.elements import EmailAddress, Footer, Header
from unstructured.partition.text import element_from_text
from unstructured.staging.base import elements_from_dicts


@pytest.mark.parametrize(
    "system",
    [PixelSpace(100, 200), PointSpace(100, 200), RelativeCoordinateSystem()],
)
def test_email_text_retains_its_coordinates_and_coordinate_system(system):
    points = (
        (0.25 * system.width, 0.25 * system.height),
        (0.25 * system.width, 0.5 * system.height),
        (0.75 * system.width, 0.5 * system.height),
        (0.75 * system.width, 0.25 * system.height),
    )

    element = element_from_text("reader@example.com", coordinates=points, coordinate_system=system)

    assert isinstance(element, EmailAddress)
    assert element.metadata.coordinates is not None
    assert element.metadata.coordinates.points == points
    assert element.metadata.coordinates.system == system
    restored = elements_from_dicts([element.to_dict()])[0]
    assert restored.metadata.coordinates == element.metadata.coordinates


def test_email_text_without_coordinates_keeps_its_existing_shape():
    element = element_from_text("reader@example.com")

    assert isinstance(element, EmailAddress)
    assert element.metadata.coordinates is None


@pytest.mark.parametrize(("y", "expected"), [(1, Header), (99, Footer)])
def test_email_text_keeps_header_and_footer_precedence(y, expected):
    points = ((10, y), (10, y), (30, y), (30, y))

    element = element_from_text(
        "reader@example.com", coordinates=points, coordinate_system=PixelSpace(100, 100)
    )

    assert isinstance(element, expected)
    assert element.metadata.coordinates.points == points
