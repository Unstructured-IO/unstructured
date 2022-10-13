import pytest
from unittest.mock import patch

import layoutparser as lp
from layoutparser.elements import Layout, Rectangle, TextBlock
import numpy as np
from PIL import Image

from unstructured.documents.pdf import PDFDocument, PDFPage
import unstructured.models.layout.detectron2 as detectron2
import unstructured.models.ocr.tesseract as tesseract


@pytest.fixture
def mock_image():
    return Image.new("1", (1, 1))


@pytest.fixture
def mock_page_layout():
    text_rectangle = Rectangle(2, 4, 6, 8)
    text_block = TextBlock(text_rectangle, text="A very repetitive narrative. " * 10, type="Text")

    title_rectangle = Rectangle(1, 2, 3, 4)
    title_block = TextBlock(title_rectangle, text="A Catchy Title", type="Title")

    return Layout([text_block, title_block])


def test_pdf_page_converts_images_to_array(mock_image):
    page = PDFPage(number=0, image=mock_image, layout=Layout())
    assert page.image_array is None

    image_array = page._get_image_array()
    assert isinstance(image_array, np.ndarray)
    assert page.image_array.all() == image_array.all()


def test_ocr(monkeypatch):
    mock_text = "The parrot flies high in the air!"

    class MockOCRAgent:
        def detect(self, *args):
            return mock_text

    monkeypatch.setattr(tesseract, "ocr_agent", MockOCRAgent)
    monkeypatch.setattr(tesseract, "is_pytesseract_available", lambda *args: True)

    image = np.random.randint(12, 24, (40, 40))
    page = PDFPage(number=0, image=image, layout=Layout())
    rectangle = Rectangle(1, 2, 3, 4)
    text_block = TextBlock(rectangle, text=None)

    assert page.ocr(text_block) == mock_text


class MockLayoutModel:
    def __init__(self, layout):
        self.layout = layout

    def detect(self, *args):
        return self.layout


def test_get_page_elements(monkeypatch, mock_page_layout):
    monkeypatch.setattr(detectron2, "model", MockLayoutModel(mock_page_layout))
    monkeypatch.setattr(detectron2, "is_detectron2_available", lambda *args: True)

    image = np.random.randint(12, 24, (40, 40))
    page = PDFPage(number=0, image=image, layout=mock_page_layout)

    elements = page.get_elements(inplace=False)

    assert str(elements[0]) == "A Catchy Title"
    assert str(elements[1]).startswith("A very repetitive narrative.")

    page.get_elements(inplace=True)
    assert elements == page.elements


def test_get_page_elements_with_ocr(monkeypatch):
    monkeypatch.setattr(PDFPage, "ocr", lambda *args: "An Even Catchier TItle")

    rectangle = Rectangle(2, 4, 6, 8)
    text_block = TextBlock(rectangle, text=None, type="Title")
    layout = Layout([text_block])

    monkeypatch.setattr(detectron2, "model", MockLayoutModel(layout))
    monkeypatch.setattr(detectron2, "is_detectron2_available", lambda *args: True)

    image = np.random.randint(12, 24, (40, 40))
    page = PDFPage(number=0, image=image, layout=layout)
    page.get_elements()

    assert str(page) == "An Even Catchier TItle"


def test_read_pdf(monkeypatch, mock_page_layout):
    image = np.random.randint(12, 24, (40, 40))
    images = [image, image]

    layouts = Layout([mock_page_layout, mock_page_layout])

    monkeypatch.setattr(detectron2, "model", MockLayoutModel(mock_page_layout))
    monkeypatch.setattr(detectron2, "is_detectron2_available", lambda *args: True)

    with patch.object(lp, "load_pdf", return_value=(layouts, images)):
        doc = PDFDocument.from_file("fake-file.pdf")

        assert str(doc).startswith("A Catchy Title")
        assert str(doc).count("A Catchy Title") == 2  ***REMOVED*** Once for each page
        assert str(doc).endswith("A very repetitive narrative. ")

        pages = doc.pages
        assert str(doc) == "\n\n".join([str(page) for page in pages])
