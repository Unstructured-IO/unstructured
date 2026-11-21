import io

import pptx
import pytest
from pptx.util import Inches

from unstructured.documents.coordinates import PointSpace
from unstructured.partition.pptx import partition_pptx


@pytest.mark.parametrize("kind", ["textbox", "title", "table", "group"])
def test_shape_coordinates_are_available_in_point_space(kind):
    presentation = pptx.Presentation()
    presentation.slide_width = Inches(10)
    presentation.slide_height = Inches(7.5)
    slide = presentation.slides.add_slide(presentation.slide_layouts[0 if kind == "title" else 6])
    if kind == "table":
        shape = slide.shapes.add_table(1, 1, Inches(1), Inches(2), Inches(3), Inches(1))
        shape.table.cell(0, 0).text = "Located content"
    elif kind == "title":
        shape = slide.shapes.title
        shape.left, shape.top, shape.width, shape.height = map(Inches, (1, 2, 3, 1))
        shape.text = "Located content"
    else:
        group = slide.shapes.add_group_shape() if kind == "group" else None
        shapes = group.shapes if group is not None else slide.shapes
        shape = shapes.add_textbox(Inches(1), Inches(2), Inches(3), Inches(1))
        shape.text = "Located content"
        if group is not None:
            group.left, group.top, group.width, group.height = map(Inches, (2, 1, 6, 2))
    file = io.BytesIO()
    presentation.save(file)

    element = partition_pptx(file=file, include_coordinates=True, languages=["eng"])[0]

    assert element.metadata.coordinates is not None
    assert element.metadata.coordinates.system == PointSpace(width=720, height=540)
    expected = (
        ((144, 468), (144, 324), (576, 324), (576, 468))
        if kind == "group"
        else ((72, 396), (72, 324), (288, 324), (288, 396))
    )
    assert element.metadata.coordinates.points == expected


def test_rotated_shape_uses_its_enclosing_rectangle():
    presentation = pptx.Presentation()
    presentation.slide_width, presentation.slide_height = Inches(10), Inches(7.5)
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    shape = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(3), Inches(1))
    shape.text = "Rotated content"
    shape.rotation = 90
    file = io.BytesIO()
    presentation.save(file)

    element = partition_pptx(file=file, include_coordinates=True, languages=["eng"])[0]

    assert element.metadata.coordinates.points == ((144, 468), (144, 252), (216, 252), (216, 468))


def test_coordinate_extraction_is_opt_in():
    presentation = pptx.Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide.shapes.add_textbox(Inches(1), Inches(1), Inches(2), Inches(1)).text = "Content"
    file = io.BytesIO()
    presentation.save(file)

    assert partition_pptx(file=file, languages=["eng"])[0].metadata.coordinates is None
