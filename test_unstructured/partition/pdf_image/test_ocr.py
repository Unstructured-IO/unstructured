from collections import namedtuple
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import unstructured_pytesseract
from lxml import etree
from pdf2image.exceptions import PDFPageCountError
from PIL import Image, UnidentifiedImageError
from unstructured_inference.inference.elements import EmbeddedTextRegion, TextRegion, TextRegions
from unstructured_inference.inference.layout import DocumentLayout, PageLayout
from unstructured_inference.inference.layoutelement import (
    LayoutElement,
    LayoutElements,
)

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.elements import ElementType
from unstructured.partition.pdf_image import ocr
from unstructured.partition.pdf_image.pdf_image_utils import (
    convert_pdf_to_images,
    pad_element_bboxes,
)
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import (
    OCR_AGENT_PADDLE,
    OCR_AGENT_TESSERACT,
    Source,
)
from unstructured.partition.utils.ocr_models.google_vision_ocr import OCRAgentGoogleVision
from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent
from unstructured.partition.utils.ocr_models.paddle_ocr import OCRAgentPaddle
from unstructured.partition.utils.ocr_models.tesseract_ocr import (
    OCRAgentTesseract,
    zoom_image,
)


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
            extracted_layout=[],
        )


@pytest.mark.parametrize("is_image", [True, False])
def test_process_file_with_ocr_invalid_filename(is_image):
    invalid_filename = "i am not a valid file name"
    with pytest.raises(FileNotFoundError):
        _ = ocr.process_file_with_ocr(
            filename=invalid_filename,
            is_image=is_image,
            out_layout=DocumentLayout(),
            extracted_layout=[],
        )


def test_supplement_page_layout_with_ocr_invalid_ocr():
    with pytest.raises(ValueError):
        _ = ocr.supplement_page_layout_with_ocr(
            page_layout=None, image=None, ocr_agent="invliad_ocr"
        )


def test_get_ocr_layout_from_image_tesseract(monkeypatch):
    monkeypatch.setattr(
        OCRAgentTesseract,
        "image_to_data_with_character_confidence_filter",
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

    ocr_agent = OCRAgentTesseract()
    ocr_layout = ocr_agent.get_layout_from_image(image)

    expected_layout = TextRegions(
        element_coords=np.array([[10.0, 5, 25, 15], [20, 15, 45, 35], [30, 25, 65, 55]]),
        texts=np.array(["Hello", "World", "!"]),
        sources=np.array([Source.OCR_TESSERACT] * 3),
    )

    assert ocr_layout.texts.tolist() == expected_layout.texts.tolist()
    np.testing.assert_array_equal(ocr_layout.element_coords, expected_layout.element_coords)
    np.testing.assert_array_equal(ocr_layout.sources, expected_layout.sources)


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


def monkeypatch_load_agent(*args):
    class MockAgent:
        def __init__(self):
            self.ocr = mock_ocr

    return MockAgent()


def test_get_ocr_layout_from_image_paddle(monkeypatch):
    monkeypatch.setattr(
        OCRAgentPaddle,
        "load_agent",
        monkeypatch_load_agent,
    )

    image = Image.new("RGB", (100, 100))

    ocr_layout = OCRAgentPaddle().get_layout_from_image(image)

    expected_layout = TextRegions(
        element_coords=np.array([[10.0, 5, 25, 15], [20, 15, 45, 35], [30, 25, 65, 55]]),
        texts=np.array(["Hello", "World", "!"]),
        sources=np.array([Source.OCR_PADDLE] * 3),
    )

    assert ocr_layout.texts.tolist() == expected_layout.texts.tolist()
    np.testing.assert_array_equal(ocr_layout.element_coords, expected_layout.element_coords)
    np.testing.assert_array_equal(ocr_layout.sources, expected_layout.sources)


def test_get_ocr_text_from_image_tesseract(monkeypatch):
    monkeypatch.setattr(
        unstructured_pytesseract,
        "image_to_string",
        lambda *args, **kwargs: "Hello World",
    )
    image = Image.new("RGB", (100, 100))

    ocr_agent = OCRAgentTesseract()
    ocr_text = ocr_agent.get_text_from_image(image)

    assert ocr_text == "Hello World"


def test_get_ocr_text_from_image_paddle(monkeypatch):
    monkeypatch.setattr(
        OCRAgentPaddle,
        "load_agent",
        monkeypatch_load_agent,
    )

    image = Image.new("RGB", (100, 100))

    ocr_agent = OCRAgentPaddle()
    ocr_text = ocr_agent.get_text_from_image(image)

    assert ocr_text == "Hello\n\nWorld\n\n!"


@pytest.fixture()
def google_vision_text_annotation():
    from google.cloud.vision import (
        Block,
        BoundingPoly,
        Page,
        Paragraph,
        Symbol,
        TextAnnotation,
        Vertex,
        Word,
    )

    breaks = TextAnnotation.DetectedBreak.BreakType
    symbols_hello = [Symbol(text=c) for c in "Hello"] + [
        Symbol(
            property=TextAnnotation.TextProperty(
                detected_break=TextAnnotation.DetectedBreak(type_=breaks.SPACE)
            )
        )
    ]
    symbols_world = [Symbol(text=c) for c in "World!"] + [
        Symbol(
            property=TextAnnotation.TextProperty(
                detected_break=TextAnnotation.DetectedBreak(type_=breaks.LINE_BREAK)
            )
        )
    ]
    words = [Word(symbols=symbols_hello), Word(symbols=symbols_world)]
    bounding_box = BoundingPoly(
        vertices=[Vertex(x=0, y=0), Vertex(x=0, y=10), Vertex(x=10, y=10), Vertex(x=10, y=0)]
    )
    paragraphs = [Paragraph(words=words, bounding_box=bounding_box)]
    blocks = [Block(paragraphs=paragraphs)]
    pages = [Page(blocks=blocks)]
    return TextAnnotation(text="Hello World!", pages=pages)


@pytest.fixture()
def google_vision_client(google_vision_text_annotation):
    Response = namedtuple("Response", "full_text_annotation")

    class FakeGoogleVisionClient:
        def document_text_detection(self, image, image_context):
            return Response(full_text_annotation=google_vision_text_annotation)

    class OCRAgentFakeGoogleVision(OCRAgentGoogleVision):
        def __init__(self, language: Optional[str] = None):
            self.client = FakeGoogleVisionClient()
            self.language = language

    return OCRAgentFakeGoogleVision()


def test_get_ocr_from_image_google_vision(google_vision_client):
    image = Image.new("RGB", (100, 100))

    ocr_agent = google_vision_client
    ocr_text = ocr_agent.get_text_from_image(image)

    assert ocr_text == "Hello World!"


def test_get_layout_from_image_google_vision(google_vision_client):
    image = Image.new("RGB", (100, 100))

    ocr_agent = google_vision_client
    regions = ocr_agent.get_layout_from_image(image)
    assert len(regions) == 1
    assert regions.texts[0] == "Hello World!"
    assert all(source == Source.OCR_GOOGLEVISION for source in regions.sources)
    assert regions.x1[0] == 0
    assert regions.y1[0] == 0
    assert regions.x2[0] == 10
    assert regions.y2[0] == 10


def test_get_layout_elements_from_image_google_vision(google_vision_client):
    image = Image.new("RGB", (100, 100))

    ocr_agent = google_vision_client
    layout_elements = ocr_agent.get_layout_elements_from_image(image)
    assert len(layout_elements) == 1


@pytest.fixture()
def mock_ocr_regions():
    return TextRegions.from_list(
        [
            EmbeddedTextRegion.from_coords(10, 10, 90, 90, text="0", source=None),
            EmbeddedTextRegion.from_coords(200, 200, 300, 300, text="1", source=None),
            EmbeddedTextRegion.from_coords(500, 320, 600, 350, text="3", source=None),
        ]
    )


@pytest.fixture()
def mock_out_layout(mock_embedded_text_regions):
    return LayoutElements.from_list(
        [
            LayoutElement(
                text="",
                source=None,
                type="Text",
                bbox=r.bbox,
            )
            for r in mock_embedded_text_regions
        ]
    )


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


@pytest.mark.parametrize("zoom", [1, 0.1, 5, -1, 0])
def test_zoom_image(zoom):
    image = Image.new("RGB", (100, 100))
    width, height = image.size
    new_image = zoom_image(image, zoom)
    new_w, new_h = new_image.size
    if zoom <= 0:
        zoom = 1
    assert new_w == np.round(width * zoom, 0)
    assert new_h == np.round(height * zoom, 0)


@pytest.fixture()
def mock_layout(mock_embedded_text_regions):
    return LayoutElements.from_list(
        [
            LayoutElement(text=r.text, type=ElementType.UNCATEGORIZED_TEXT, bbox=r.bbox)
            for r in mock_embedded_text_regions
        ]
    )


def test_supplement_layout_with_ocr_elements(mock_layout, mock_ocr_regions):
    ocr_elements = [
        LayoutElement(text=r.text, source=None, type=ElementType.UNCATEGORIZED_TEXT, bbox=r.bbox)
        for r in mock_ocr_regions.as_list()
    ]

    final_layout = ocr.supplement_layout_with_ocr_elements(mock_layout, mock_ocr_regions).as_list()

    # Check if the final layout contains the original layout elements
    for element in mock_layout.as_list():
        assert element in final_layout

    # Check if the final layout contains the OCR-derived elements
    assert any(ocr_element in final_layout for ocr_element in ocr_elements)

    # Check if the OCR-derived elements that are subregions of layout elements are removed
    for element in mock_layout.as_list():
        for ocr_element in ocr_elements:
            if ocr_element.bbox.is_almost_subregion_of(
                element.bbox,
                env_config.OCR_LAYOUT_SUBREGION_THRESHOLD,
            ):
                assert ocr_element not in final_layout


def test_merge_out_layout_with_ocr_layout(mock_out_layout, mock_ocr_regions):
    ocr_elements = [
        LayoutElement(text=r.text, source=None, type=ElementType.UNCATEGORIZED_TEXT, bbox=r.bbox)
        for r in mock_ocr_regions.as_list()
    ]
    input_layout_elements = mock_out_layout.as_list()

    final_layout = ocr.merge_out_layout_with_ocr_layout(
        mock_out_layout,
        mock_ocr_regions,
    ).as_list()

    # Check if the out layout's text attribute is updated with aggregated OCR text
    assert final_layout[0].text == mock_ocr_regions.texts[2]

    # Check if the final layout contains both original elements and OCR-derived elements
    # The first element's text is modified by the ocr regions so it won't be the same as the input
    assert all(element in final_layout for element in input_layout_elements[1:])
    assert final_layout[0].bbox == input_layout_elements[0].bbox
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
    return TextRegions.from_list(
        [
            TextRegion.from_coords(x1=15, y1=25, x2=35, y2=45, text="Token1"),
            TextRegion.from_coords(x1=40, y1=30, x2=45, y2=50, text="Token2"),
        ]
    )


def test_supplement_element_with_table_extraction():
    from unstructured_inference.models import tables

    tables.load_agent()

    image = next(convert_pdf_to_images(example_doc_path("pdf/single_table.pdf")))
    elements = LayoutElements(
        element_coords=np.array([[215.00109863, 731.89996338, 1470.07739258, 972.83129883]]),
        texts=np.array(["foo"]),
        sources=np.array(["yolox_sg"]),
        element_class_ids=np.array([0]),
        element_class_id_map={0: "Table"},
    )
    supplemented = ocr.supplement_element_with_table_extraction(
        elements=elements,
        image=image,
        tables_agent=tables.tables_agent,
        ocr_agent=ocr.OCRAgent.get_agent(language="eng"),
    )
    assert supplemented.text_as_html[0].startswith("<table>")


def test_get_table_tokens(mock_ocr_layout):
    with patch.object(OCRAgentTesseract, "get_layout_from_image", return_value=mock_ocr_layout):
        ocr_agent = OCRAgent.get_agent(language="eng")
        table_tokens = ocr.get_table_tokens(table_element_image=None, ocr_agent=ocr_agent)
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


def test_auto_zoom_not_exceed_tesseract_limit(monkeypatch):
    monkeypatch.setenv("TESSERACT_MIN_TEXT_HEIGHT", "1000")
    monkeypatch.setenv("TESSERACT_OPTIMUM_TEXT_HEIGHT", "100000")
    monkeypatch.setattr(
        OCRAgentTesseract,
        "image_to_data_with_character_confidence_filter",
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

    image = Image.new("RGB", (1000, 1000))
    ocr_agent = OCRAgentTesseract()
    # tests that the code can run instead of oom and OCR results make sense
    assert ocr_agent.get_layout_from_image(image).texts.tolist() == [
        "Hello",
        "World",
        "!",
    ]


def test_merge_out_layout_with_cid_code(mock_out_layout, mock_ocr_regions):
    # the code should ignore this invalid text and use ocr region's text
    mock_out_layout.texts = mock_out_layout.texts.astype(object)
    mock_out_layout.texts[0] = "(cid:10)(cid:5)?"
    ocr_elements = [
        LayoutElement(text=r.text, source=None, type=ElementType.UNCATEGORIZED_TEXT, bbox=r.bbox)
        for r in mock_ocr_regions.as_list()
    ]
    input_layout_elements = mock_out_layout.as_list()

    # TODO (yao): refactor the tests to check the array data structure directly instead of
    # converting them into lists first (this includes other tests in this file)
    final_layout = ocr.merge_out_layout_with_ocr_layout(mock_out_layout, mock_ocr_regions).as_list()

    # Check if the out layout's text attribute is updated with aggregated OCR text
    assert final_layout[0].text == mock_ocr_regions.texts[2]

    # Check if the final layout contains both original elements and OCR-derived elements
    assert all(element in final_layout for element in input_layout_elements[1:])
    assert any(element in final_layout for element in ocr_elements)


def _create_hocr_word_span(
    characters: list[tuple[str, str]], word_bbox: tuple[int, int, int, int], namespace_map: dict
) -> etree.Element:
    word_span = [
        '<root xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n',
        (
            f"<span class='ocrx_word' title='"
            f"bbox {word_bbox[0]} {word_bbox[1]} {word_bbox[2]} {word_bbox[3]}"
            f"; x_wconf 64'>"
        ),
    ]
    for char, x_conf in characters:
        word_span.append(
            f"<span class='ocrx_cinfo' title='x_bboxes 0 0 0 0; x_conf {x_conf}'>{char}</span>"
        )
    word_span.append("</span>")
    word_span.append("</root>")
    root = etree.fromstring("\n".join(word_span))
    return root


def test_extract_word_from_hocr():
    characters = [
        ("w", "99.0"),
        ("o", "98.5"),
        ("r", "97.5"),
        ("d", "96.0"),
        ("!", "50.0"),
        ("@", "45.0"),
    ]
    word_bbox = (10, 9, 70, 22)
    agent = OCRAgentTesseract()
    word_span = _create_hocr_word_span(characters, word_bbox, agent.hocr_namespace)

    text = agent.extract_word_from_hocr(word_span, 0.0)
    assert text == "word!@"

    text = agent.extract_word_from_hocr(word_span, 0.960)
    assert text == "word"

    text = agent.extract_word_from_hocr(word_span, 0.990)
    assert text == "w"

    text = agent.extract_word_from_hocr(word_span, 0.999)
    assert text == ""


def test_hocr_to_dataframe():
    characters = [
        ("w", "99.0"),
        ("o", "98.5"),
        ("r", "97.5"),
        ("d", "96.0"),
        ("!", "50.0"),
        ("@", "45.0"),
    ]
    word_bbox = (10, 9, 70, 22)
    agent = OCRAgentTesseract()
    hocr = etree.tostring(_create_hocr_word_span(characters, word_bbox, agent.hocr_namespace))
    df = agent.hocr_to_dataframe(hocr=hocr, character_confidence_threshold=0.960)

    assert df.shape == (1, 5)
    assert df["left"].iloc[0] == 10
    assert df["top"].iloc[0] == 9
    assert df["width"].iloc[0] == 60
    assert df["height"].iloc[0] == 13
    assert df["text"].iloc[0] == "word"


def test_hocr_to_dataframe_when_no_prediction_empty_df():
    df = OCRAgentTesseract().hocr_to_dataframe(hocr="")

    assert df.shape == (0, 5)
    assert "left" in df.columns
    assert "top" in df.columns
    assert "width" in df.columns
    assert "height" in df.columns
    assert "text" in df.columns


@pytest.fixture
def mock_page(mock_ocr_layout, mock_layout):
    mock_page = MagicMock(PageLayout)
    mock_page.elements_array = mock_layout
    return mock_page


def test_supplement_layout_with_ocr(mocker, mock_page):
    from unstructured.partition.pdf_image.ocr import OCRAgent

    mocker.patch.object(OCRAgent, "get_layout_from_image", return_value=mock_ocr_layout)
    spy = mocker.spy(OCRAgent, "get_instance")

    ocr.supplement_page_layout_with_ocr(
        mock_page,
        Image.new("RGB", (100, 100)),
        infer_table_structure=True,
        ocr_agent=OCR_AGENT_TESSERACT,
        ocr_languages="eng",
        table_ocr_agent=OCR_AGENT_PADDLE,
    )

    assert spy.call_args_list[0][1] == {"language": "eng", "ocr_agent_module": OCR_AGENT_TESSERACT}
    assert spy.call_args_list[1][1] == {"language": "en", "ocr_agent_module": OCR_AGENT_PADDLE}


def test_pass_down_agents(mocker, mock_page):
    from unstructured.partition.pdf_image.ocr import OCRAgent, PILImage

    mocker.patch.object(OCRAgent, "get_layout_from_image", return_value=mock_ocr_layout)
    mocker.patch.object(PILImage, "open", return_value=Image.new("RGB", (100, 100)))
    spy = mocker.spy(OCRAgent, "get_instance")
    doc = MagicMock(DocumentLayout)
    doc.pages = [mock_page]

    ocr.process_file_with_ocr(
        "foo",
        doc,
        [],
        infer_table_structure=True,
        is_image=True,
        ocr_agent=OCR_AGENT_PADDLE,
        ocr_languages="eng",
        table_ocr_agent=OCR_AGENT_TESSERACT,
    )

    assert spy.call_args_list[0][1] == {"language": "en", "ocr_agent_module": OCR_AGENT_PADDLE}
    assert spy.call_args_list[1][1] == {"language": "eng", "ocr_agent_module": OCR_AGENT_TESSERACT}
