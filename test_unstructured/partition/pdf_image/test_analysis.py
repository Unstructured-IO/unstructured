import numpy as np
import pytest
from PIL import Image
from unstructured_inference.inference.elements import Rectangle
from unstructured_inference.inference.layout import DocumentLayout, PageLayout
from unstructured_inference.inference.layoutelement import LayoutElement

from unstructured.partition.pdf_image.analysis.bbox_visualisation import (
    TextAlignment,
    get_bbox_text_size,
    get_bbox_thickness,
    get_label_rect_and_coords,
    get_rgb_color,
    get_text_color,
)
from unstructured.partition.pdf_image.analysis.layout_dump import ObjectDetectionLayoutDumper


@pytest.mark.parametrize("color", ["red", "green", "blue", "yellow", "black", "white"])
def test_get_rgb_color(color: str):
    color_tuple = get_rgb_color(color)

    assert isinstance(color_tuple, tuple)
    assert len(color_tuple) == 3
    assert all(isinstance(c, int) for c in color_tuple)
    assert all(0 <= c <= 255 for c in color_tuple)


@pytest.mark.parametrize(
    ("bbox", "expected_text_size"),
    [
        ((0, 0, 90, 90), 17),
        ((0, 0, 500, 200), 21),
        ((0, 0, 10000, 10000), 32),
    ],
)
def test_get_bbox_text_size(bbox: tuple[int, int, int, int], expected_text_size):
    page_size = (1700, 2200)  # standard size of a page
    text_size = get_bbox_text_size(bbox, page_size)

    assert text_size == expected_text_size


@pytest.mark.parametrize(
    ("bbox", "expected_box_thickness"),
    [
        ((0, 0, 90, 90), 1),
        ((0, 0, 450, 250), 2),
        ((0, 0, 600, 1000), 3),
    ],
)
def test_get_bbox_thickness(bbox: tuple[int, int, int, int], expected_box_thickness):
    page_size = (1700, 2200)  # standard size of a page
    box_thickness = get_bbox_thickness(bbox, page_size)

    assert box_thickness == expected_box_thickness


@pytest.mark.parametrize(
    ("color", "expected_text_color"),
    [
        ("navy", "white"),
        ("crimson", "white"),
        ("maroon", "white"),
        ("dimgray", "white"),
        ("darkgreen", "white"),
        ("darkcyan", "white"),
        ("fuchsia", "white"),
        ("violet", "black"),
        ("gold", "black"),
        ("aqua", "black"),
        ("greenyellow", "black"),
    ],
)
def test_best_text_color(color, expected_text_color):
    color_tuple = get_rgb_color(color)
    expected_text_color_tuple = get_rgb_color(expected_text_color)

    _, text_color_tuple = get_text_color(color_tuple)
    assert text_color_tuple == expected_text_color_tuple


@pytest.mark.parametrize(
    ("alignment", "expected_text_bbox"),
    [
        (TextAlignment.CENTER, ((145, 145), (155, 155))),
        (TextAlignment.TOP_LEFT, ((100, 90), (120, 100))),
        (TextAlignment.TOP_RIGHT, ((180, 100), (200, 110))),
        (TextAlignment.BOTTOM_LEFT, ((100, 190), (120, 200))),
        (TextAlignment.BOTTOM_RIGHT, ((180, 190), (200, 200))),
    ],
)
def test_get_text_bbox(alignment, expected_text_bbox):
    text_bbox, text_xy = get_label_rect_and_coords(
        alignment=alignment, bbox_points=(100, 100, 200, 200), text_width=10, text_height=10
    )
    # adding high atol to account for the text-based extending of the bbox
    assert np.allclose(text_bbox, expected_text_bbox, atol=10)


def test_od_document_layout_dump():
    page1 = PageLayout(
        number=1,
        image=Image.new("1", (1, 1)),
        image_metadata={"width": 100, "height": 100},
    )
    page1.elements = [
        LayoutElement(type="Title", bbox=Rectangle(x1=0, y1=0, x2=10, y2=10), prob=0.7),
        LayoutElement(type="Paragraph", bbox=Rectangle(x1=0, y1=100, x2=10, y2=110), prob=0.8),
    ]
    page2 = PageLayout(
        number=2,
        image=Image.new("1", (1, 1)),
        image_metadata={"width": 100, "height": 100},
    )
    page2.elements = [
        LayoutElement(type="Table", bbox=Rectangle(x1=0, y1=0, x2=10, y2=10), prob=0.9),
        LayoutElement(type="Image", bbox=Rectangle(x1=0, y1=100, x2=10, y2=110), prob=1.0),
    ]
    od_document_layout = DocumentLayout(pages=[page1, page2])

    expected_dump = {
        "pages": [
            {
                "number": 1,
                "size": {
                    "width": 100,
                    "height": 100,
                },
                "elements": [
                    {"bbox": [0, 0, 10, 10], "type": "Title", "prob": 0.7},
                    {"bbox": [0, 100, 10, 110], "type": "Paragraph", "prob": 0.8},
                ],
            },
            {
                "number": 2,
                "size": {
                    "width": 100,
                    "height": 100,
                },
                "elements": [
                    {"bbox": [0, 0, 10, 10], "type": "Table", "prob": 0.9},
                    {"bbox": [0, 100, 10, 110], "type": "Image", "prob": 1.0},
                ],
            },
        ]
    }
    od_layout_dump = ObjectDetectionLayoutDumper(od_document_layout).dump()

    assert expected_dump == {"pages": od_layout_dump.get("pages")}

    # check OD model classes are attached but do not depend on a specific model instance
    assert "object_detection_classes" in od_layout_dump
    assert len(od_layout_dump["object_detection_classes"]) > 0
