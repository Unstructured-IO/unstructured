import pytest
import unstructured_pytesseract
from pdf2image.exceptions import PDFPageCountError
from PIL import Image, UnidentifiedImageError
from unstructured_inference.inference.elements import EmbeddedTextRegion, TextRegion
from unstructured_inference.inference.layout import DocumentLayout
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
)

from unstructured.partition import ocr
from unstructured.partition.ocr import pad_element_bboxes
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


# TODO(yuming): Add this for test coverage, please update/move it in CORE-1886
def test_supplement_page_layout_with_ocr_invalid_ocr(monkeypatch):
    monkeypatch.setenv("ENTIRE_PAGE_OCR", "invalid_ocr")
    with pytest.raises(ValueError):
        _ = ocr.supplement_page_layout_with_ocr(
            page_layout=None,
            image=None,
        )


def test_get_ocr_layout_from_image_tesseract(monkeypatch):
    monkeypatch.setattr(
        unstructured_pytesseract,
        "image_to_data",
        lambda *args, **kwargs: {
            "level": ["line", "line", "word"],
            "left": [10, 20, 30],
            "top": [5, 15, 25],
            "width": [15, 25, 35],
            "height": [10, 20, 30],
            "text": ["Hello", "World", "!"],
        },
    )

    image = Image.new("RGB", (100, 100))

    ocr_layout = ocr.get_ocr_layout_from_image(
        image,
        ocr_languages="eng",
        entire_page_ocr="tesseract",
    )

    expected_layout = [
        TextRegion(10, 5, 25, 15, "Hello", source="OCR-tesseract"),
        TextRegion(20, 15, 45, 35, "World", source="OCR-tesseract"),
        TextRegion(30, 25, 65, 55, "!", source="OCR-tesseract"),
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

    ocr_layout = ocr.get_ocr_layout_from_image(image, ocr_languages="eng", entire_page_ocr="paddle")

    expected_layout = [
        TextRegion(10, 5, 25, 15, "Hello", source="OCR-paddle"),
        TextRegion(20, 15, 45, 35, "World", source="OCR-paddle"),
        TextRegion(30, 25, 65, 55, "!", source="OCR-paddle"),
    ]

    assert ocr_layout == expected_layout


def test_get_ocr_text_from_image_tesseract(monkeypatch):
    monkeypatch.setattr(
        unstructured_pytesseract,
        "image_to_string",
        lambda *args, **kwargs: {"text": "Hello World"},
    )
    image = Image.new("RGB", (100, 100))

    ocr_text = ocr.get_ocr_text_from_image(image, ocr_languages="eng", entire_page_ocr="tesseract")

    assert ocr_text == "Hello World"


def test_get_ocr_text_from_image_paddle(monkeypatch):
    monkeypatch.setattr(
        paddle_ocr,
        "load_agent",
        monkeypatch_load_agent,
    )

    image = Image.new("RGB", (100, 100))

    ocr_text = ocr.get_ocr_text_from_image(image, ocr_languages="eng", entire_page_ocr="paddle")

    assert ocr_text == "HelloWorld!"


@pytest.fixture()
def mock_ocr_regions():
    return [
        EmbeddedTextRegion(10, 10, 90, 90, text="0", source=None),
        EmbeddedTextRegion(200, 200, 300, 300, text="1", source=None),
        EmbeddedTextRegion(500, 320, 600, 350, text="3", source=None),
    ]


@pytest.fixture()
def mock_out_layout(mock_embedded_text_regions):
    return [
        LayoutElement(
            r.x1,
            r.y1,
            r.x2,
            r.y2,
            text=None,
            source=None,
            type="Text",
        )
        for r in mock_embedded_text_regions
    ]


def test_aggregate_ocr_text_by_block():
    expected = "A Unified Toolkit"
    ocr_layout = [
        TextRegion(0, 0, 20, 20, "A"),
        TextRegion(50, 50, 150, 150, "Unified"),
        TextRegion(150, 150, 300, 250, "Toolkit"),
        TextRegion(200, 250, 300, 350, "Deep"),
    ]
    region = TextRegion(0, 0, 250, 350, "")

    text = ocr.aggregate_ocr_text_by_block(ocr_layout, region, 0.5)
    assert text == expected


def test_merge_text_regions(mock_embedded_text_regions):
    expected = TextRegion(
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
        LayoutElement(
            x1=437.83888888888885,
            y1=317.319341111111,
            x2=1256.334784222222,
            y2=406.9837855555556,
            text="LayoutParser: A Unified Toolkit for Deep Learning Based Document Image",
            type="UncategorizedText",
        ),
    ]

    elements = ocr.get_elements_from_ocr_regions(mock_embedded_text_regions)
    assert elements == expected


@pytest.fixture()
def mock_layout(mock_embedded_text_regions):
    return [
        LayoutElement(
            r.x1,
            r.y1,
            r.x2,
            r.y2,
            text=r.text,
            type="UncategorizedText",
        )
        for r in mock_embedded_text_regions
    ]


@pytest.fixture()
def mock_embedded_text_regions():
    return [
        EmbeddedTextRegion(
            x1=453.00277777777774,
            y1=317.319341111111,
            x2=711.5338541666665,
            y2=358.28571222222206,
            text="LayoutParser:",
        ),
        EmbeddedTextRegion(
            x1=726.4778125,
            y1=317.319341111111,
            x2=760.3308594444444,
            y2=357.1698966666667,
            text="A",
        ),
        EmbeddedTextRegion(
            x1=775.2748177777777,
            y1=317.319341111111,
            x2=917.3579885555555,
            y2=357.1698966666667,
            text="Unified",
        ),
        EmbeddedTextRegion(
            x1=932.3019468888888,
            y1=317.319341111111,
            x2=1071.8426522222221,
            y2=357.1698966666667,
            text="Toolkit",
        ),
        EmbeddedTextRegion(
            x1=1086.7866105555556,
            y1=317.319341111111,
            x2=1141.2105142777777,
            y2=357.1698966666667,
            text="for",
        ),
        EmbeddedTextRegion(
            x1=1156.154472611111,
            y1=317.319341111111,
            x2=1256.334784222222,
            y2=357.1698966666667,
            text="Deep",
        ),
        EmbeddedTextRegion(
            x1=437.83888888888885,
            y1=367.13322999999986,
            x2=610.0171992222222,
            y2=406.9837855555556,
            text="Learning",
        ),
        EmbeddedTextRegion(
            x1=624.9611575555555,
            y1=367.13322999999986,
            x2=741.6754646666665,
            y2=406.9837855555556,
            text="Based",
        ),
        EmbeddedTextRegion(
            x1=756.619423,
            y1=367.13322999999986,
            x2=958.3867708333332,
            y2=406.9837855555556,
            text="Document",
        ),
        EmbeddedTextRegion(
            x1=973.3307291666665,
            y1=367.13322999999986,
            x2=1092.0535042777776,
            y2=406.9837855555556,
            text="Image",
        ),
    ]


def test_supplement_layout_with_ocr_elements(mock_layout, mock_ocr_regions):
    ocr_elements = [
        LayoutElement(
            r.x1,
            r.y1,
            r.x2,
            r.y2,
            text=r.text,
            source=None,
            type="UncategorizedText",
        )
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
            if ocr_element.is_almost_subregion_of(element, ocr.SUBREGION_THRESHOLD_FOR_OCR):
                assert ocr_element not in final_layout


def test_merge_out_layout_with_ocr_layout(mock_out_layout, mock_ocr_regions):
    ocr_elements = [
        LayoutElement(
            r.x1,
            r.y1,
            r.x2,
            r.y2,
            text=r.text,
            source=None,
            type="UncategorizedText",
        )
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
    element = LayoutElement(
        x1=10,
        y1=20,
        x2=30,
        y2=40,
        text="",
        source=None,
        type="UncategorizedText",
    )
    expected_original_element_bbox = (10, 20, 30, 40)

    padded_element = pad_element_bboxes(element, padding)

    padded_element_bbox = (
        padded_element.x1,
        padded_element.y1,
        padded_element.x2,
        padded_element.y2,
    )
    assert padded_element_bbox == expected_bbox

    # make sure the original element has not changed
    original_element_bbox = (element.x1, element.y1, element.x2, element.y2)
    assert original_element_bbox == expected_original_element_bbox
