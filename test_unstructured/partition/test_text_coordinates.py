import pytest

from unstructured.documents.coordinates import (
    CoordinateSystem,
    PixelSpace,
    PointSpace,
    RelativeCoordinateSystem,
)
from unstructured.documents.elements import Footer, Header
from unstructured.partition.text import element_from_text


@pytest.mark.parametrize(
    "system",
    [
        PixelSpace(100, 200),
        PointSpace(72, 144),
        CoordinateSystem(100, 200),
        RelativeCoordinateSystem(),
    ],
)
@pytest.mark.parametrize(
    ("top", "bottom", "category"),
    [(2, 8, "Header"), (192, 198, "Footer"), (90, 110, None)],
)
def test_text_classification_uses_the_physical_page_position(
    system: CoordinateSystem, top: float, bottom: float, category: str | None
):
    screen = PixelSpace(100, 200)
    points = screen.convert_multiple_coordinates_to_new_system(
        system, ((10, top), (10, bottom), (90, bottom), (90, top))
    )

    element = element_from_text("Document label", coordinates=points, coordinate_system=system)

    if category is None:
        assert not isinstance(element, (Header, Footer))
    else:
        assert element.category == category
    assert element.text == "Document label"
    assert element.metadata.coordinates.points == points
    assert element.metadata.coordinates.system is system
