from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import unstructured_pytesseract
from pdf2image.exceptions import PDFPageCountError
from PIL import Image, UnidentifiedImageError
from unstructured_inference.inference.elements import EmbeddedTextRegion, TextRegion
from unstructured_inference.inference.layout import DocumentLayout
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
)

from unstructured.documents.elements import ElementType
from unstructured.partition import ocr
from unstructured.partition.ocr import pad_element_bboxes
from unstructured.partition.utils.constants import (
    OCR_AGENT_PADDLE,
    OCR_AGENT_TESSERACT,
    Source,
)
from unstructured.partition.utils.ocr_models import paddle_ocr


@pytest.mark.parametrize(
    ("is_image", "expected_error"),
    [
        (True, UnidentifiedImageError),
        (False, PDFPageCountError),
    ],
)
def test_process_data_with_ocr_invalid_file(is_image, expected_error):
    invalid_data = b"i am not a valid file"
    with pytest.raises(expected_error):
        _ = ocr.process_data_with_ocr(
            data=invalid_data,
            is_image=is_image,
            out_layout=DocumentLayout(),
        )


@pytest.mark.parametrize(
    ("is_image"),
    [
        (True),
        (False),
    ],
)
def test_process_file_with_ocr_invalid_filename(is_image):
    invalid_filename = "i am not a valid file name"
    with pytest.raises(FileNotFoundError):
        _ = ocr.process_file_with_ocr(
            filename=invalid_filename,
            is_image=is_image,
            out_layout=DocumentLayout(),
        )


def test_supplement_page_layout_with_ocr_invalid_ocr(monkeypatch):
    monkeypatch.setenv("OCR_AGENT", "invalid_ocr")
    with pytest.raises(ValueError):
        _ = ocr.supplement_page_layout_with_ocr(
            page_layout=None,
            image=None,
        )


def test_get_ocr_layout_from_image_tesseract(monkeypatch):
    monkeypatch.setattr(
        unstructured_pytesseract,
        "image_to_data",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "left": [10, 20, 30, 0],
                "top": [5, 15, 25, 0],
                "width": [15, 25, 35, 0],
                "height": [10, 20, 30, 0],
                "text": ["Hello", "World", "!", ""],
            },
        ),
    )

    image = Image.new("RGB", (100, 100))

    ocr_layout = ocr.get_ocr_layout_from_image(
        image,
        ocr_languages="eng",
        ocr_agent=OCR_AGENT_TESSERACT,
    )

    expected_layout = [
        TextRegion.from_coords(10, 5, 25, 15, "Hello", source=Source.OCR_TESSERACT),
        TextRegion.from_coords(20, 15, 45, 35, "World", source=Source.OCR_TESSERACT),
        TextRegion.from_coords(30, 25, 65, 55, "!", source=Source.OCR_TESSERACT),
    ]

    assert ocr_layout == expected_layout


def mock_ocr(*args, **kwargs):
    return [
        [
            (
                [(10, 5), (25, 5), (25, 15), (10, 15)],
                ["Hello"],
            ),
        ],
        [
            (
                [(20, 15), (45, 15), (45, 35), (20, 35)],
                ["World"],
            ),
        ],
        [
            (
                [(30, 25), (65, 25), (65, 55), (30, 55)],
                ["!"],
            ),
        ],
        [
            (
                [(0, 0), (0, 0), (0, 0), (0, 0)],
                [""],
            ),
        ],
    ]


def monkeypatch_load_agent():
    class MockAgent:
        def __init__(self):
            self.ocr = mock_ocr

    return MockAgent()


def test_get_ocr_layout_from_image_paddle(monkeypatch):
    monkeypatch.setattr(
        paddle_ocr,
        "load_agent",
        monkeypatch_load_agent,
    )

    image = Image.new("RGB", (100, 100))

    ocr_layout = ocr.get_ocr_layout_from_image(
        image,
        ocr_languages="eng",
        ocr_agent=OCR_AGENT_PADDLE,
    )

    expected_layout = [
        TextRegion.from_coords(10, 5, 25, 15, "Hello", source=Source.OCR_PADDLE),
        TextRegion.from_coords(20, 15, 45, 35, "World", source=Source.OCR_PADDLE),
        TextRegion.from_coords(30, 25, 65, 55, "!", source=Source.OCR_PADDLE),
    ]

    assert ocr_layout == expected_layout


def test_get_ocr_text_from_image_tesseract(monkeypatch):
    monkeypatch.setattr(
        unstructured_pytesseract,
        "image_to_string",
        lambda *args, **kwargs: "Hello World",
    )
    image = Image.new("RGB", (100, 100))

    ocr_text = ocr.get_ocr_text_from_image(
        image,
        ocr_languages="eng",
        ocr_agent=OCR_AGENT_TESSERACT,
    )

    assert ocr_text == "Hello World"


def test_get_ocr_text_from_image_paddle(monkeypatch):
    monkeypatch.setattr(
        paddle_ocr,
        "load_agent",
        monkeypatch_load_agent,
    )

    image = Image.new("RGB", (100, 100))

    ocr_text = ocr.get_ocr_text_from_image(
        image,
        ocr_languages="eng",
        ocr_agent=OCR_AGENT_PADDLE,
    )

    assert ocr_text == "Hello\n\nWorld\n\n!"


@pytest.fixture()
def mock_ocr_regions():
    return [
        EmbeddedTextRegion.from_coords(10, 10, 90, 90, text="0", source=None),
        EmbeddedTextRegion.from_coords(200, 200, 300, 300, text="1", source=None),
        EmbeddedTextRegion.from_coords(500, 320, 600, 350, text="3", source=None),
    ]


@pytest.fixture()
def mock_out_layout(mock_embedded_text_regions):
    return [
        LayoutElement(
            text=None,
            source=None,
            type="Text",
            bbox=r.bbox,
        )
        for r in mock_embedded_text_regions
    ]


def test_aggregate_ocr_text_by_block():
    expected = "A Unified Toolkit"
    ocr_layout = [
        TextRegion.from_coords(0, 0, 20, 20, "A"),
        TextRegion.from_coords(50, 50, 150, 150, "Unified"),
        TextRegion.from_coords(150, 150, 300, 250, "Toolkit"),
        TextRegion.from_coords(200, 250, 300, 350, "Deep"),
    ]
    region = TextRegion.from_coords(0, 0, 250, 350, "")

    text = ocr.aggregate_ocr_text_by_block(ocr_layout, region, 0.5)
    assert text == expected


def test_merge_text_regions(mock_embedded_text_regions):
    expected = TextRegion.from_coords(
        x1=437.83888888888885,
        y1=317.319341111111,
        x2=1256.334784222222,
        y2=406.9837855555556,
        text="LayoutParser: A Unified Toolkit for Deep Learning Based Document Image",
    )

    merged_text_region = ocr.merge_text_regions(mock_embedded_text_regions)
    assert merged_text_region == expected


def test_get_elements_from_ocr_regions(mock_embedded_text_regions):
    expected = [
        LayoutElement.from_coords(
            x1=437.83888888888885,
            y1=317.319341111111,
            x2=1256.334784222222,
            y2=406.9837855555556,
            text="LayoutParser: A Unified Toolkit for Deep Learning Based Document Image",
            type=ElementType.UNCATEGORIZED_TEXT,
        ),
    ]

    elements = ocr.get_elements_from_ocr_regions(mock_embedded_text_regions)
    assert elements == expected


@pytest.mark.parametrize("zoom", [1, 0.1, 5, -1, 0])
def test_zoom_image(zoom):
    image = Image.new("RGB", (100, 100))
    width, height = image.size
    new_image = ocr.zoom_image(image, zoom)
    new_w, new_h = new_image.size
    if zoom <= 0:
        zoom = 1
    assert new_w == np.round(width * zoom, 0)
    assert new_h == np.round(height * zoom, 0)


@pytest.fixture()
def mock_layout(mock_embedded_text_regions):
    return [
        LayoutElement(text=r.text, type=ElementType.UNCATEGORIZED_TEXT, bbox=r.bbox)
        for r in mock_embedded_text_regions
    ]


@pytest.fixture()
def mock_embedded_text_regions():
    return [
        EmbeddedTextRegion.from_coords(
            x1=453.00277777777774,
            y1=317.319341111111,
            x2=711.5338541666665,
            y2=358.28571222222206,
            text="LayoutParser:",
        ),
        EmbeddedTextRegion.from_coords(
            x1=726.4778125,
            y1=317.319341111111,
            x2=760.3308594444444,
            y2=357.1698966666667,
            text="A",
        ),
        EmbeddedTextRegion.from_coords(
            x1=775.2748177777777,
            y1=317.319341111111,
            x2=917.3579885555555,
            y2=357.1698966666667,
            text="Unified",
        ),
        EmbeddedTextRegion.from_coords(
            x1=932.3019468888888,
            y1=317.319341111111,
            x2=1071.8426522222221,
            y2=357.1698966666667,
            text="Toolkit",
        ),
        EmbeddedTextRegion.from_coords(
            x1=1086.7866105555556,
            y1=317.319341111111,
            x2=1141.2105142777777,
            y2=357.1698966666667,
            text="for",
        ),
        EmbeddedTextRegion.from_coords(
            x1=1156.154472611111,
            y1=317.319341111111,
            x2=1256.334784222222,
            y2=357.1698966666667,
            text="Deep",
        ),
        EmbeddedTextRegion.from_coords(
            x1=437.83888888888885,
            y1=367.13322999999986,
            x2=610.0171992222222,
            y2=406.9837855555556,
            text="Learning",
        ),
        EmbeddedTextRegion.from_coords(
            x1=624.9611575555555,
            y1=367.13322999999986,
            x2=741.6754646666665,
            y2=406.9837855555556,
            text="Based",
        ),
        EmbeddedTextRegion.from_coords(
            x1=756.619423,
            y1=367.13322999999986,
            x2=958.3867708333332,
            y2=406.9837855555556,
            text="Document",
        ),
        EmbeddedTextRegion.from_coords(
            x1=973.3307291666665,
            y1=367.13322999999986,
            x2=1092.0535042777776,
            y2=406.9837855555556,
            text="Image",
        ),
    ]


def test_supplement_layout_with_ocr_elements(mock_layout, mock_ocr_regions):
    ocr_elements = [
        LayoutElement(text=r.text, source=None, type=ElementType.UNCATEGORIZED_TEXT, bbox=r.bbox)
        for r in mock_ocr_regions
    ]

    final_layout = ocr.supplement_layout_with_ocr_elements(mock_layout, mock_ocr_regions)

    # Check if the final layout contains the original layout elements
    for element in mock_layout:
        assert element in final_layout

    # Check if the final layout contains the OCR-derived elements
    assert any(ocr_element in final_layout for ocr_element in ocr_elements)

    # Check if the OCR-derived elements that are subregions of layout elements are removed
    for element in mock_layout:
        for ocr_element in ocr_elements:
            if ocr_element.bbox.is_almost_subregion_of(
                element.bbox,
                ocr.SUBREGION_THRESHOLD_FOR_OCR,
            ):
                assert ocr_element not in final_layout


def test_merge_out_layout_with_ocr_layout(mock_out_layout, mock_ocr_regions):
    ocr_elements = [
        LayoutElement(text=r.text, source=None, type=ElementType.UNCATEGORIZED_TEXT, bbox=r.bbox)
        for r in mock_ocr_regions
    ]

    final_layout = ocr.merge_out_layout_with_ocr_layout(mock_out_layout, mock_ocr_regions)

    # Check if the out layout's text attribute is updated with aggregated OCR text
    assert final_layout[0].text == mock_ocr_regions[2].text

    # Check if the final layout contains both original elements and OCR-derived elements
    assert all(element in final_layout for element in mock_out_layout)
    assert any(element in final_layout for element in ocr_elements)


@pytest.mark.parametrize(
    ("padding", "expected_bbox"),
    [
        (5, (5, 15, 35, 45)),
        (-3, (13, 23, 27, 37)),
        (2.5, (7.5, 17.5, 32.5, 42.5)),
        (-1.5, (11.5, 21.5, 28.5, 38.5)),
    ],
)
def test_pad_element_bboxes(padding, expected_bbox):
    element = LayoutElement.from_coords(
        x1=10,
        y1=20,
        x2=30,
        y2=40,
        text="",
        source=None,
        type=ElementType.UNCATEGORIZED_TEXT,
    )
    expected_original_element_bbox = (10, 20, 30, 40)

    padded_element = pad_element_bboxes(element, padding)

    padded_element_bbox = (
        padded_element.bbox.x1,
        padded_element.bbox.y1,
        padded_element.bbox.x2,
        padded_element.bbox.y2,
    )
    assert padded_element_bbox == expected_bbox

    # make sure the original element has not changed
    original_element_bbox = (element.bbox.x1, element.bbox.y1, element.bbox.x2, element.bbox.y2)
    assert original_element_bbox == expected_original_element_bbox


@pytest.fixture()
def table_element():
    table = LayoutElement.from_coords(x1=10, y1=20, x2=50, y2=70, text="I am a table", type="Table")
    return table


@pytest.fixture()
def mock_ocr_layout():
    ocr_regions = [
        TextRegion.from_coords(x1=15, y1=25, x2=35, y2=45, text="Token1"),
        TextRegion.from_coords(x1=40, y1=30, x2=45, y2=50, text="Token2"),
    ]
    return ocr_regions


def test_get_table_tokens(mock_ocr_layout):
    with patch.object(ocr, "get_ocr_layout_from_image", return_value=mock_ocr_layout):
        table_tokens = ocr.get_table_tokens(image=None)
        expected_tokens = [
            {
                "bbox": [15, 25, 35, 45],
                "text": "Token1",
                "span_num": 0,
                "line_num": 0,
                "block_num": 0,
            },
            {
                "bbox": [40, 30, 45, 50],
                "text": "Token2",
                "span_num": 1,
                "line_num": 0,
                "block_num": 0,
            },
        ]

        assert table_tokens == expected_tokens
