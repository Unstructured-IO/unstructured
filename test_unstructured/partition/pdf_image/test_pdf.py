from __future__ import annotations

import base64
import logging
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from tempfile import SpooledTemporaryFile
from unittest import mock

import pytest
from pdf2image.exceptions import PDFPageCountError
from PIL import Image
from pytest_mock import MockFixture
from unstructured_inference.inference import layout
from unstructured_inference.inference.elements import Rectangle
from unstructured_inference.inference.layout import DocumentLayout, PageLayout
from unstructured_inference.inference.layoutelement import LayoutElement

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import (
    CoordinatesMetadata,
    Element,
    ElementMetadata,
    ElementType,
    Footer,
    Header,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.errors import PageCountExceededError
from unstructured.partition import pdf, strategies
from unstructured.partition.pdf_image import ocr, pdfminer_processing
from unstructured.partition.pdf_image.pdfminer_processing import get_uris_from_annots
from unstructured.partition.utils.constants import (
    SORT_MODE_BASIC,
    SORT_MODE_DONT,
    SORT_MODE_XY_CUT,
    UNSTRUCTURED_INCLUDE_DEBUG_METADATA,
    PartitionStrategy,
)


class MockResponse:
    def __init__(self, status_code, response):
        self.status_code = status_code
        self.response = response

    def json(self):
        return self.response


def mock_healthy_get(url, **kwargs):
    return MockResponse(status_code=200, response={})


def mock_unhealthy_get(url, **kwargs):
    return MockResponse(status_code=500, response={})


def mock_unsuccessful_post(url, **kwargs):
    return MockResponse(status_code=500, response={})


def mock_successful_post(url, **kwargs):
    response = {
        "pages": [
            {
                "number": 0,
                "elements": [
                    {"type": "Title", "text": "Charlie Brown and the Great Pumpkin"},
                ],
            },
            {
                "number": 1,
                "elements": [{"type": "Title", "text": "A Charlie Brown Christmas"}],
            },
        ],
    }
    return MockResponse(status_code=200, response=response)


class MockPageLayout(layout.PageLayout):
    def __init__(self, number: int, image: Image):
        self.number = number
        self.image = image
        self.image_metadata = {"width": 10, "height": 10}
        self.detection_model = None
        self.elements = [
            layout.LayoutElement.from_coords(
                type="Title",
                x1=0.0,
                y1=0.0,
                x2=2.0,
                y2=2.0,
                text="Charlie Brown and the Great Pumpkin",
            ),
        ]
        self.elements_array = layout.LayoutElements.from_list(self.elements)


class MockSinglePageLayout(layout.PageLayout):
    def __init__(self, number: int, image: Image.Image):
        self.number = number
        self.image = image
        self.image_metadata = {"width": 10, "height": 10}

    @property
    def elements(self):
        return [
            LayoutElement(
                type="Headline",
                text="Charlie Brown and the Great Pumpkin",
                bbox=Rectangle(None, None, None, None),
            ),
            LayoutElement(
                type="Subheadline",
                text="The Beginning",
                bbox=Rectangle(None, None, None, None),
            ),
            LayoutElement(
                type="Text",
                text="This time Charlie Brown had it really tricky...",
                bbox=Rectangle(None, None, None, None),
            ),
            LayoutElement(
                type="Title",
                text="Another book title in the same page",
                bbox=Rectangle(None, None, None, None),
            ),
        ]

    @property
    def elements_array(self):
        return layout.LayoutElements.from_list(self.elements)


class MockDocumentLayout(layout.DocumentLayout):
    @property
    def pages(self):
        return [
            MockPageLayout(number=0, image=Image.new("1", (1, 1))),
            MockPageLayout(number=1, image=Image.new("1", (1, 1))),
        ]


class MockSinglePageDocumentLayout(layout.DocumentLayout):
    @property
    def pages(self):
        return [
            MockSinglePageLayout(number=1, image=Image.new("1", (1, 1))),
        ]


@pytest.mark.parametrize(
    ("filename", "file"),
    [
        (example_doc_path("pdf/layout-parser-paper-fast.pdf"), None),
        (None, b"0000"),
    ],
)
def test_partition_pdf_local(monkeypatch, filename, file):
    monkeypatch.setattr(
        layout,
        "process_data_with_model",
        lambda *args, **kwargs: MockDocumentLayout(),
    )
    monkeypatch.setattr(
        layout,
        "process_file_with_model",
        lambda *args, **kwargs: MockDocumentLayout(),
    )
    monkeypatch.setattr(
        pdfminer_processing,
        "process_data_with_pdfminer",
        lambda *args, **kwargs: MockDocumentLayout(),
    )
    monkeypatch.setattr(
        pdfminer_processing,
        "process_file_with_pdfminer",
        lambda *args, **kwargs: MockDocumentLayout(),
    )
    monkeypatch.setattr(
        ocr,
        "process_data_with_ocr",
        lambda *args, **kwargs: MockDocumentLayout(),
    )
    monkeypatch.setattr(
        ocr,
        "process_file_with_ocr",
        lambda *args, **kwargs: MockDocumentLayout(),
    )

    partition_pdf_response = pdf._partition_pdf_or_image_local(filename, file)
    assert partition_pdf_response[0].text == "Charlie Brown and the Great Pumpkin"


def test_partition_pdf_local_raises_with_no_filename():
    with pytest.raises((FileNotFoundError, PDFPageCountError)):
        pdf._partition_pdf_or_image_local(filename="", file=None, is_image=False)


@pytest.mark.parametrize("file_mode", ["filename", "rb", "spool"])
@pytest.mark.parametrize(
    ("strategy", "starting_page_number", "expected_page_numbers", "origin"),
    # fast: can't capture the "intentionally left blank page" page
    # others: will ignore the actual blank page
    [
        (PartitionStrategy.FAST, 1, {1, 4}, {"pdfminer"}),
        (PartitionStrategy.FAST, 3, {3, 6}, {"pdfminer"}),
        (PartitionStrategy.HI_RES, 4, {4, 6, 7}, {"yolox", "pdfminer", "ocr_tesseract"}),
        (PartitionStrategy.OCR_ONLY, 1, {1, 3, 4}, {"ocr_tesseract"}),
    ],
)
def test_partition_pdf_outputs_valid_amount_of_elements_and_metadata_values(
    file_mode,
    strategy,
    starting_page_number,
    expected_page_numbers,
    origin,
    filename=example_doc_path("pdf/layout-parser-paper-with-empty-pages.pdf"),
):
    # Test that the partition_pdf function can handle filename
    def _test(result):
        # validate that the result is a non-empty list of dicts
        assert len(result) > 10
        # check that the pdf has multiple different page numbers
        assert {element.metadata.page_number for element in result} == expected_page_numbers
        if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
            print(
                [
                    (element.metadata.detection_origin, element.category, element.text)
                    for element in result
                ]
            )
            assert {element.metadata.detection_origin for element in result} == origin

    if file_mode == "filename":
        result = pdf.partition_pdf(
            filename=filename, strategy=strategy, starting_page_number=starting_page_number
        )
        _test(result)
    elif file_mode == "rb":
        with open(filename, "rb") as f:
            result = pdf.partition_pdf(
                file=f, strategy=strategy, starting_page_number=starting_page_number
            )
            _test(result)
    else:
        with open(filename, "rb") as test_file:
            with SpooledTemporaryFile() as spooled_temp_file:
                spooled_temp_file.write(test_file.read())
                spooled_temp_file.seek(0)
                result = pdf.partition_pdf(
                    file=spooled_temp_file,
                    strategy=strategy,
                    starting_page_number=starting_page_number,
                )
            _test(result)


@mock.patch.dict(os.environ, {"UNSTRUCTURED_HI_RES_MODEL_NAME": "checkbox"})
def test_partition_pdf_with_model_name_env_var(
    monkeypatch,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])
    with mock.patch.object(
        layout,
        "process_file_with_model",
        return_value=MockDocumentLayout(),
    ) as mock_process:
        pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.HI_RES)
        assert mock_process.call_args[1]["model_name"] == "checkbox"


@pytest.mark.parametrize("model_name", ["checkbox", "yolox"])
def test_partition_pdf_with_model_name(
    monkeypatch,
    model_name,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])
    with mock.patch.object(
        layout,
        "process_file_with_model",
        return_value=MockDocumentLayout(),
    ) as mock_process:
        pdf.partition_pdf(
            filename=filename,
            strategy=PartitionStrategy.HI_RES,
            model_name=model_name,
        )
        assert mock_process.call_args[1]["model_name"] == model_name

    with mock.patch.object(
        layout,
        "process_data_with_model",
        return_value=MockDocumentLayout(),
    ) as mock_process:
        with open(filename, "rb") as f:
            pdf.partition_pdf(
                file=f,
                strategy=PartitionStrategy.HI_RES,
                model_name=model_name,
            )
            assert mock_process.call_args[1]["model_name"] == model_name


def test_partition_pdf_with_hi_res_model_name(
    monkeypatch,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])
    with mock.patch.object(
        layout,
        "process_file_with_model",
        return_value=MockDocumentLayout(),
    ) as mock_process:
        pdf.partition_pdf(
            filename=filename, strategy=PartitionStrategy.HI_RES, hi_res_model_name="checkbox"
        )
        # unstructured-ingest uses `model_name` instead of `hi_res_model_name`
        assert mock_process.call_args[1]["model_name"] == "checkbox"


def test_partition_pdf_or_image_with_hi_res_model_name(
    monkeypatch,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])
    with mock.patch.object(
        layout,
        "process_file_with_model",
        return_value=MockDocumentLayout(),
    ) as mock_process:
        pdf.partition_pdf_or_image(
            filename=filename, strategy=PartitionStrategy.HI_RES, hi_res_model_name="checkbox"
        )
        # unstructured-ingest uses `model_name` instead of `hi_res_model_name`
        assert mock_process.call_args[1]["model_name"] == "checkbox"


def test_partition_pdf_with_auto_strategy(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    elements = pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.AUTO)
    title = "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis"
    assert elements[6].text == title
    assert elements[6].metadata.filename == "layout-parser-paper-fast.pdf"
    assert elements[6].metadata.file_directory == os.path.dirname(filename)


def test_partition_pdf_with_page_breaks(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    elements = pdf.partition_pdf(filename=filename, url=None, include_page_breaks=True)
    assert "PageBreak" in [elem.category for elem in elements]


def test_partition_pdf_with_no_page_breaks(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    elements = pdf.partition_pdf(filename=filename, url=None)
    assert "PageBreak" not in [elem.category for elem in elements]


def test_partition_pdf_with_fast_strategy(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    elements = pdf.partition_pdf(
        filename=filename, url=None, strategy=PartitionStrategy.FAST, starting_page_number=3
    )
    assert len(elements) > 10
    # check that the pdf has multiple different page numbers
    assert {element.metadata.page_number for element in elements} == {3, 4}
    for element in elements:
        assert element.metadata.filename == "layout-parser-paper-fast.pdf"


def test_partition_pdf_with_fast_neg_coordinates():
    filename = example_doc_path("pdf/negative-coords.pdf")
    elements = pdf.partition_pdf(filename=filename, url=None, strategy=PartitionStrategy.FAST)
    assert len(elements) == 5
    assert elements[0].metadata.coordinates.points[0][0] < 0
    assert elements[0].metadata.coordinates.points[1][0] < 0


def test_partition_pdf_with_fast_groups_text(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    elements = pdf.partition_pdf(filename=filename, url=None, strategy=PartitionStrategy.FAST)

    first_narrative_element = None
    for element in elements:
        if isinstance(element, NarrativeText):
            first_narrative_element = element
            break
    assert len(first_narrative_element.text) > 1000
    assert first_narrative_element.text.startswith("Abstract. Recent advances")
    assert first_narrative_element.text.endswith("https://layout-parser.github.io.")
    assert first_narrative_element.metadata.filename == "layout-parser-paper-fast.pdf"


def test_partition_pdf_with_fast_strategy_from_file(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(file=f, url=None, strategy=PartitionStrategy.FAST)
    assert len(elements) > 10


def test_partition_pdf_with_fast_strategy_and_page_breaks(
    caplog,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    elements = pdf.partition_pdf(
        filename=filename,
        url=None,
        strategy=PartitionStrategy.FAST,
        include_page_breaks=True,
    )
    assert len(elements) > 10
    assert "PageBreak" in [elem.category for elem in elements]

    assert "unstructured_inference is not installed" not in caplog.text
    for element in elements:
        assert element.metadata.filename == "layout-parser-paper-fast.pdf"


def test_partition_pdf_raises_with_bad_strategy(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    with pytest.raises(ValueError):
        pdf.partition_pdf(filename=filename, url=None, strategy="made_up")


def test_partition_pdf_falls_back_to_fast(
    monkeypatch,
    caplog,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    def mock_exists(dep):
        return dep not in ["unstructured_inference", "unstructured_pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)

    mock_return = [[Text("Hello there!")], []]
    with mock.patch.object(
        pdf,
        "extractable_elements",
        return_value=mock_return,
    ) as mock_partition:
        pdf.partition_pdf(filename=filename, url=None, strategy=PartitionStrategy.HI_RES)

    mock_partition.assert_called_once()
    assert "unstructured_inference is not installed" in caplog.text


def test_partition_pdf_falls_back_to_fast_from_ocr_only(
    monkeypatch,
    caplog,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    def mock_exists(dep):
        return dep not in ["unstructured_pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)

    mock_return = [[Text("Hello there!")], []]
    with mock.patch.object(
        pdf,
        "extractable_elements",
        return_value=mock_return,
    ) as mock_partition, mock.patch.object(
        pdf,
        "_partition_pdf_or_image_with_ocr",
    ) as mock_partition_ocr:
        pdf.partition_pdf(filename=filename, url=None, strategy=PartitionStrategy.OCR_ONLY)

    mock_partition.assert_called_once()
    mock_partition_ocr.assert_not_called()
    assert "pytesseract is not installed" in caplog.text


def test_partition_pdf_falls_back_to_hi_res_from_ocr_only(
    monkeypatch,
    caplog,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    def mock_exists(dep):
        return dep not in ["unstructured_pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])

    mock_return = [Text("Hello there!")]
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_local",
        return_value=mock_return,
    ) as mock_partition:
        pdf.partition_pdf(filename=filename, url=None, strategy=PartitionStrategy.OCR_ONLY)

    mock_partition.assert_called_once()
    assert "pytesseract is not installed" in caplog.text


def test_partition_pdf_falls_back_to_ocr_only(
    monkeypatch,
    caplog,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    def mock_exists(dep):
        return dep not in ["unstructured_inference"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)

    mock_return = [Text("Hello there!")]
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_with_ocr",
        return_value=mock_return,
    ) as mock_partition:
        pdf.partition_pdf(filename=filename, url=None, strategy=PartitionStrategy.HI_RES)

    mock_partition.assert_called_once()
    assert "unstructured_inference is not installed" in caplog.text


def test_partition_pdf_uses_table_extraction():
    filename = example_doc_path("pdf/layout-parser-paper-fast.pdf")
    with mock.patch(
        "unstructured.partition.pdf_image.ocr.process_file_with_ocr",
    ) as mock_process_file_with_model:
        pdf.partition_pdf(filename, infer_table_structure=True)
        assert mock_process_file_with_model.call_args[1]["infer_table_structure"]


@pytest.mark.parametrize(
    "ocr_mode",
    [
        "entire_page",
        "individual_blocks",
    ],
)
def test_partition_pdf_hi_table_extraction_with_languages(ocr_mode):
    filename = example_doc_path("pdf/korean-text-with-tables.pdf")
    elements = pdf.partition_pdf(
        filename=filename,
        ocr_mode=ocr_mode,
        languages=["kor"],
        strategy=PartitionStrategy.HI_RES,
        infer_table_structure=True,
    )
    table = [el.metadata.text_as_html for el in elements if el.metadata.text_as_html]
    assert elements[0].metadata.languages == ["kor"]
    assert len(table) == 2
    assert "<table><thead><tr>" in table[0]
    assert "</thead><tbody><tr>" in table[0]
    # FIXME(yuming): didn't test full sentence here since unit test and docker test have
    # some differences on spaces between characters
    assert "업" in table[0]


@pytest.mark.parametrize(
    "strategy",
    [
        PartitionStrategy.FAST,
        PartitionStrategy.HI_RES,
        PartitionStrategy.OCR_ONLY,
    ],
)
def test_partition_pdf_strategies_keep_languages_metadata(strategy):
    filename = example_doc_path("pdf/korean-text-with-tables.pdf")
    elements = pdf.partition_pdf(
        filename=filename,
        languages=["kor"],
        strategy=strategy,
    )
    assert elements[0].metadata.languages == ["kor"]


@pytest.mark.parametrize(
    "ocr_mode",
    [
        "entire_page",
        "individual_blocks",
    ],
)
def test_partition_pdf_hi_res_ocr_mode_with_table_extraction(ocr_mode):
    filename = example_doc_path("pdf/layout-parser-paper.pdf")
    elements = pdf.partition_pdf(
        filename=filename,
        ocr_mode=ocr_mode,
        strategy=PartitionStrategy.HI_RES,
        infer_table_structure=True,
    )
    table = [el.metadata.text_as_html for el in elements if el.metadata.text_as_html]
    assert len(table) == 2
    assert "<table><thead><tr>" in table[0]
    assert "</thead><tbody><tr>" in table[0]
    assert "Layouts of history Japanese documents" in table[0]
    assert "Layouts of scanned modern magazines and scientific report" in table[0]
    assert "Layouts of scanned US newspapers from the 20th century" in table[0]


def test_partition_pdf_with_copy_protection():
    filename = example_doc_path("pdf/copy-protected.pdf")
    elements = pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.HI_RES)
    title = "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis"
    idx = 22
    assert elements[idx].text == title
    assert {element.metadata.page_number for element in elements} == {1, 2}
    assert elements[idx].metadata.detection_class_prob is not None
    assert isinstance(elements[idx].metadata.detection_class_prob, float)


def test_partition_pdf_with_dpi():
    filename = example_doc_path("pdf/copy-protected.pdf")
    with mock.patch.object(
        layout, "process_file_with_model", return_value=MockDocumentLayout()
    ) as mock_process:
        pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.HI_RES, pdf_image_dpi=100)
        assert mock_process.call_args[1]["pdf_image_dpi"] == 100


def test_partition_pdf_requiring_recursive_text_grab(filename=example_doc_path("pdf/reliance.pdf")):
    elements = pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.FAST)
    assert len(elements) > 50
    assert elements[0].metadata.page_number == 1
    assert elements[-1].metadata.page_number == 3


def test_partition_pdf_text_not_extractable():
    filename = example_doc_path("pdf/loremipsum-flat.pdf")
    elements = pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.FAST)
    assert len(elements) == 0


def test_partition_pdf_fails_if_pdf_not_processable(
    monkeypatch,
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    def mock_exists(dep):
        return dep not in ["unstructured_inference", "unstructured_pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])

    with pytest.raises(ValueError):
        pdf.partition_pdf(filename=filename)


def test_partition_pdf_fast_groups_text_in_text_box():
    filename = example_doc_path("pdf/chevron-page.pdf")
    elements = pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.FAST)
    expected_coordinate_points_0 = (
        (193.1741, 71.94000000000005),
        (193.1741, 91.94000000000005),
        (418.6881, 91.94000000000005),
        (418.6881, 71.94000000000005),
    )
    expected_coordinate_system_0 = PixelSpace(width=612, height=792)
    expected_elem_metadata_0 = ElementMetadata(
        coordinates=CoordinatesMetadata(
            points=expected_coordinate_points_0,
            system=expected_coordinate_system_0,
        ),
    )
    assert elements[0] == Title(
        "eastern mediterranean",
        metadata=expected_elem_metadata_0,
    )
    assert isinstance(elements[1], NarrativeText)
    assert str(elements[1]).startswith("We")
    assert str(elements[1]).endswith("Jordan and Egypt.")

    expected_coordinate_points_3 = (
        (95.6683, 181.16470000000004),
        (95.6683, 226.16470000000004),
        (166.7908, 226.16470000000004),
        (166.7908, 181.16470000000004),
    )
    expected_coordinate_system_3 = PixelSpace(width=612, height=792)
    expected_elem_metadata_3 = ElementMetadata(
        coordinates=CoordinatesMetadata(
            points=expected_coordinate_points_3,
            system=expected_coordinate_system_3,
        ),
    )
    assert elements[2] == Text("2.5", metadata=expected_elem_metadata_3)


def test_partition_pdf_with_metadata_filename(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    elements = pdf.partition_pdf(
        filename=filename,
        url=None,
        include_page_breaks=True,
        metadata_filename="test",
    )
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_pdf_with_fast_strategy_from_file_with_metadata_filename(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(
            file=f,
            url=None,
            strategy=PartitionStrategy.FAST,
            metadata_filename="test",
        )
    for element in elements:
        assert element.metadata.filename == "test"


@pytest.mark.parametrize("file_mode", ["filename", "rb", "spool"])
@pytest.mark.parametrize(
    "strategy",
    [
        PartitionStrategy.AUTO,
        PartitionStrategy.HI_RES,
        PartitionStrategy.FAST,
        PartitionStrategy.OCR_ONLY,
    ],
)
@pytest.mark.parametrize("metadata_last_modified", [None, "2020-07-05T09:24:28"])
def test_partition_pdf_metadata_date(
    mocker: MockFixture,
    file_mode: str,
    strategy: str,
    metadata_last_modified: str | None,
):
    filename = example_doc_path("pdf/copy-protected.pdf")
    filesystem_last_modified = "2029-07-05T09:24:28"
    expected_last_modified = (
        metadata_last_modified if metadata_last_modified else filesystem_last_modified
    )
    if not metadata_last_modified and file_mode != "filename":
        expected_last_modified = None

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    if file_mode == "filename":
        elements = pdf.partition_pdf(
            filename=filename,
            strategy=strategy,
            metadata_last_modified=metadata_last_modified,
        )
    elif file_mode == "rb":
        with open(filename, "rb") as f:
            elements = pdf.partition_pdf(
                file=f,
                strategy=strategy,
                metadata_last_modified=metadata_last_modified,
            )
    else:
        with open(filename, "rb") as test_file:
            with SpooledTemporaryFile() as spooled_temp_file:
                spooled_temp_file.write(test_file.read())
                spooled_temp_file.seek(0)
                elements = pdf.partition_pdf(
                    file=spooled_temp_file,
                    strategy=strategy,
                    metadata_last_modified=metadata_last_modified,
                )

    assert {el.metadata.last_modified for el in elements} == {expected_last_modified}


@pytest.mark.parametrize("strategy", [PartitionStrategy.FAST, PartitionStrategy.HI_RES])
def test_partition_pdf_with_json(strategy: str):
    elements = pdf.partition_pdf(
        example_doc_path("pdf/layout-parser-paper-fast.pdf"),
        strategy=strategy,
    )
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_by_title_on_partition_pdf(
    filename=example_doc_path("pdf/layout-parser-paper-fast.pdf"),
):
    elements = pdf.partition_pdf(filename=filename)
    chunk_elements = pdf.partition_pdf(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_pdf_formats_languages_for_tesseract():
    filename = example_doc_path("pdf/DA-1p.pdf")
    with mock.patch.object(ocr, "process_file_with_ocr", mock.MagicMock()) as mock_process:
        pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.HI_RES, languages=["en"])
        assert mock_process.call_args[1]["ocr_languages"] == "eng"


def test_partition_pdf_warns_with_ocr_languages(caplog):
    filename = example_doc_path("pdf/chevron-page.pdf")
    pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.HI_RES, ocr_languages="eng")
    assert "The ocr_languages kwarg will be deprecated" in caplog.text


def test_partition_categorization_backup():
    text = "This is Clearly a Title"
    with mock.patch.object(pdf, "_partition_pdf_or_image_local", return_value=[Text(text)]):
        elements = pdf.partition_pdf_or_image(
            example_doc_path("pdf/layout-parser-paper-fast.pdf"),
            strategy=PartitionStrategy.HI_RES,
        )
        # Should have changed the element class from Text to Title
        assert isinstance(elements[0], Title)
        assert elements[0].text == text


@pytest.mark.parametrize(
    "filename",
    [example_doc_path("pdf/layout-parser-paper-fast.pdf")],
)
def test_combine_numbered_list(filename):
    elements = pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.AUTO)
    first_list_element = None
    for element in elements:
        if isinstance(element, ListItem):
            first_list_element = element
            break
    assert len(elements) < 28
    assert len([element for element in elements if isinstance(element, ListItem)]) == 4
    assert first_list_element.text.endswith(
        "character recognition, and other DIA tasks (Section 3)",
    )


@pytest.mark.parametrize(
    ("filename", "strategy"),
    [
        (example_doc_path("pdf/layout-parser-paper-fast.pdf"), "fast"),
        (example_doc_path("pdf/layout-parser-paper-fast.pdf"), "hi_res"),
    ],
)
def test_partition_pdf_hyperlinks(filename, strategy):
    elements = pdf.partition_pdf(filename=filename, strategy=strategy)
    links = [
        {
            "text": "8",
            "url": "cite.gardner2018allennlp",
            "start_index": 138,
        },
        {
            "text": "34",
            "url": "cite.wolf2019huggingface",
            "start_index": 141,
        },
        {
            "text": "35",
            "url": "cite.wu2019detectron2",
            "start_index": 168,
        },
    ]
    assert elements[-1].metadata.links == links


@pytest.mark.parametrize(
    ("filename", "strategy"),
    [
        (example_doc_path("pdf/embedded-link.pdf"), "fast"),
        (example_doc_path("pdf/embedded-link.pdf"), "hi_res"),
    ],
)
def test_partition_pdf_hyperlinks_multiple_lines(filename, strategy):
    elements = pdf.partition_pdf(filename=filename, strategy=strategy)
    assert elements[-1].metadata.links[-1]["text"] == "capturing"
    assert len(elements[-1].metadata.links) == 2


def test_partition_pdf_uses_model_name():
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_local",
    ) as mockpartition:
        pdf.partition_pdf(
            example_doc_path("pdf/layout-parser-paper-fast.pdf"),
            model_name="test",
            strategy=PartitionStrategy.HI_RES,
        )

        mockpartition.assert_called_once()
        assert "model_name" in mockpartition.call_args.kwargs
        assert mockpartition.call_args.kwargs["model_name"]


def test_partition_pdf_uses_hi_res_model_name():
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_local",
    ) as mockpartition:
        pdf.partition_pdf(
            example_doc_path("pdf/layout-parser-paper-fast.pdf"),
            hi_res_model_name="test",
            strategy=PartitionStrategy.HI_RES,
        )

        mockpartition.assert_called_once()
        assert "hi_res_model_name" in mockpartition.call_args.kwargs
        assert mockpartition.call_args.kwargs["hi_res_model_name"]


def test_partition_pdf_word_bbox_not_char(
    filename=example_doc_path("pdf/interface-config-guide-p93.pdf"),
):
    try:
        elements = pdf.partition_pdf(filename=filename, strategy="fast")
    except Exception as e:
        raise ("Partitioning fail: %s" % e)
    assert len(elements) == 17


def test_partition_pdf_fast_no_mapping_errors(
    filename=example_doc_path("pdf/a1977-backus-p21.pdf"),
):
    """Verify there is no regression for https://github.com/Unstructured-IO/unstructured/pull/2940,
    failing to map old parent_id's to new"""
    pdf.partition_pdf(filename=filename, strategy="fast")


def test_partition_pdf_raises_TypeError_for_invalid_languages():
    filename = example_doc_path("pdf/chevron-page.pdf")
    with pytest.raises(TypeError):
        pdf.partition_pdf(filename=filename, strategy=PartitionStrategy.HI_RES, languages="eng")


@pytest.mark.parametrize(
    ("threshold", "expected"),
    [
        (0.4, [True, False, False, False, False]),
        (0.1, [True, True, False, False, False]),
    ],
)
def test_check_annotations_within_element(threshold, expected):
    annotations = [
        {"bbox": [0, 0, 1, 1], "page_number": 1},
        {"bbox": [0, 0, 3, 1], "page_number": 1},
        {"bbox": [0, 0, 1, 1], "page_number": 2},
        {"bbox": [0, 0, 0, 1], "page_number": 1},
        {"bbox": [3, 0, 4, 1], "page_number": 1},
    ]
    element_bbox = (0, 0, 1, 1)
    filtered = pdf.check_annotations_within_element(annotations, element_bbox, 1, threshold)
    results = [annotation in filtered for annotation in annotations]
    assert results == expected


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        (None, "yolox"),
        ("test", "test"),
    ],
)
def test_default_hi_res_model(env, expected, monkeypatch):
    if env is not None:
        monkeypatch.setenv("UNSTRUCTURED_HI_RES_MODEL_NAME", env)
    assert pdf.default_hi_res_model() == expected


def test_partition_model_name_default_to_None():
    filename = example_doc_path("pdf/DA-1p.pdf")
    try:
        pdf.partition_pdf(
            filename=filename,
            strategy=PartitionStrategy.HI_RES,
            ocr_languages="eng",
            model_name=None,
        )
    except AttributeError:
        pytest.fail("partition_pdf() raised AttributeError unexpectedly!")


def test_partition_hi_res_model_name_default_to_None():
    filename = example_doc_path("pdf/DA-1p.pdf")
    try:
        pdf.partition_pdf(
            filename=filename,
            strategy=PartitionStrategy.HI_RES,
            hi_res_model_name=None,
        )
    except AttributeError:
        pytest.fail("partition_pdf() raised AttributeError unexpectedly!")


@pytest.mark.parametrize(
    ("strategy", "ocr_func"),
    [
        (
            PartitionStrategy.HI_RES,
            "unstructured_pytesseract.image_to_pdf_or_hocr",
        ),
        (
            PartitionStrategy.OCR_ONLY,
            "unstructured_pytesseract.image_to_pdf_or_hocr",
        ),
        (
            PartitionStrategy.OCR_ONLY,
            "unstructured_pytesseract.image_to_string",
        ),
    ],
)
def test_ocr_language_passes_through(strategy, ocr_func):
    # Create an exception that will be raised directly after OCR is called to stop execution
    class CallException(Exception):
        pass

    mock_ocr_func = mock.Mock(side_effect=CallException("Function called!"))
    # Patch the ocr function with the mock that will record the call and then terminate
    with mock.patch(ocr_func, mock_ocr_func), pytest.raises(CallException):
        pdf.partition_pdf(
            example_doc_path("pdf/layout-parser-paper-fast.pdf"),
            strategy=strategy,
            ocr_languages="kor",
        )
    # Check that the language parameter was passed down as expected
    kwargs = mock_ocr_func.call_args.kwargs
    assert "lang" in kwargs
    assert kwargs["lang"] == "kor"


@pytest.mark.parametrize(
    ("annots", "height", "coordinate_system", "page_number", "expected"),
    [
        (["BS", "BE"], 300, PixelSpace(300, 300), 1, 0),
        (
            [
                {
                    "Type": "/'Annot'",
                    "Subtype": "/'Link'",
                    "A": {
                        "Type": "/'Action'",
                        "S": "/'URI'",
                        "URI": "b'https://layout-parser.github.io'",
                    },
                    "BS": {"S": "/'S'", "W": 1},
                    "Border": [0, 0, 1],
                    "C": [0, 1, 1],
                    "H": "/'I'",
                    "Rect": [304.055, 224.156, 452.472, 234.368],
                },
                {
                    "Type": "/'Annot'",
                    "Subtype": "/'Link'",
                    "A": {"S": "/'GoTo'", "D": "b'cite.harley2015evaluation'"},
                    "BS": {"S": "/'S'", "W": 1},
                    "Border": [0, 0, 1],
                    "C": [0, 1, 0],
                    "H": "/'I'",
                    "Rect": (468.305, 128.081, 480.26, 136.494),
                },
            ],
            792,
            PixelSpace(612, 792),
            1,
            2,
        ),
        (
            [
                {
                    "Type": "/'Annot'",
                    "Subtype": "/'Link'",
                    "A": {
                        "Type": "/'Action'",
                        "S": "/'URI'",
                        "URI": "b'https://layout-parser.github.io'",
                    },
                    "BS": {"S": "/'S'", "W": 1},
                    "Border": [0, 0, 1],
                    "C": [0, 1, 1],
                    "H": "/'I'",
                    "Rect": "I am not a tuple or list!",
                },
                {
                    "Type": "/'Annot'",
                    "Subtype": "/'Link'",
                    "A": {"S": "/'GoTo'", "D": "b'cite.harley2015evaluation'"},
                    "BS": {"S": "/'S'", "W": 1},
                    "Border": [0, 0, 1],
                    "C": [0, 1, 0],
                    "H": "/'I'",
                    "Rect": (468.305, 128.081, 480.26),
                },
            ],
            792,
            PixelSpace(612, 792),
            1,
            0,
        ),
    ],
)
def test_get_uris_from_annots_string_annotation(
    annots, height, coordinate_system, page_number, expected
):
    annotation_list = get_uris_from_annots(annots, height, coordinate_system, page_number)
    assert len(annotation_list) == expected


@pytest.mark.parametrize("file_mode", ["filename", "rb", "spool"])
@pytest.mark.parametrize(
    ("filename", "is_image"),
    [
        (example_doc_path("pdf/layout-parser-paper-fast.pdf"), False),
        (example_doc_path("img/layout-parser-paper-fast.jpg"), True),
    ],
)
def test_partition_pdf_with_ocr_only_strategy(
    file_mode,
    filename,
    is_image,
):
    if file_mode == "filename":
        elements = pdf.partition_pdf(
            filename=filename,
            strategy=PartitionStrategy.OCR_ONLY,
            languages=["eng"],
            is_image=is_image,
        )
    elif file_mode == "rb":
        with open(filename, "rb") as f:
            elements = pdf.partition_pdf(
                file=f,
                strategy=PartitionStrategy.OCR_ONLY,
                languages=["eng"],
                is_image=is_image,
            )
    else:
        with open(filename, "rb") as test_file:
            with SpooledTemporaryFile() as spooled_temp_file:
                spooled_temp_file.write(test_file.read())
                spooled_temp_file.seek(0)
                elements = pdf.partition_pdf(
                    file=spooled_temp_file,
                    strategy=PartitionStrategy.OCR_ONLY,
                    languages=["eng"],
                    is_image=is_image,
                )

    assert elements[0].metadata.languages == ["eng"]
    # check pages
    if is_image:
        assert {el.metadata.page_number for el in elements} == {1}
    else:
        assert {el.metadata.page_number for el in elements} == {1, 2}

    # check coordinates
    for element in elements:
        if element.metadata.coordinates:
            for point in element.metadata.coordinates.points:
                if point[0] and point[1]:
                    assert point[0] is not math.nan
                    assert point[1] is not math.nan

    # check detection origin
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"ocr_tesseract"}


def test_partition_pdf_with_all_number_table_and_ocr_only_strategy():
    # AttributeError was previously being raised when partitioning documents that contained only
    # numerical values with `strategy=PartitionStrategy.OCR_ONLY`
    filename = example_doc_path("pdf/all-number-table.pdf")
    assert pdf.partition_pdf(filename, strategy=PartitionStrategy.OCR_ONLY)


# As of pdfminer 221105, this pdf throws an error and requires a workaround
# See #2059
def test_partition_pdf_with_bad_color_profile():
    filename = example_doc_path("pdf/pdf-bad-color-space.pdf")
    assert pdf.partition_pdf(filename, strategy="fast")


def test_partition_pdf_with_fast_finds_headers_footers(
    filename=example_doc_path("pdf/header-test-doc.pdf"),
):
    elements = pdf.partition_pdf(filename, strategy="fast")
    assert isinstance(elements[0], Header)
    assert isinstance(elements[-1], Footer)
    assert [element.text for element in elements] == [
        "I Am A Header",
        "Title",
        "Here is a lovely sentences.",
        "I Am A Footer",
    ]


@pytest.mark.parametrize(
    ("filename", "expected_log"),
    [
        # This one is *actually* an invalid PDF document
        ("invalid-pdf-structure-pdfminer-entire-doc.pdf", "Repairing the PDF document ..."),
    ],
)
def test_extractable_elements_repair_invalid_pdf_structure(filename, expected_log, caplog):
    caplog.set_level(logging.INFO)
    assert pdf.extractable_elements(filename=example_doc_path(f"pdf/{filename}"))
    assert expected_log in caplog.text


@pytest.mark.parametrize(
    ("filename", "expected_log"),
    [
        # This one is *not* an invalid PDF document, make sure we
        # don't try to "repair" it unnecessarily
        ("invalid-pdf-structure-pdfminer-one-page.pdf", "Repairing the PDF page 2 ..."),
    ],
)
def test_properly_patch_pdfminer(filename, expected_log, caplog):
    caplog.set_level(logging.INFO)
    assert pdf.extractable_elements(filename=example_doc_path(f"pdf/{filename}"))
    assert expected_log not in caplog.text


def assert_element_extraction(
    elements: list[Element],
    extract_image_block_types: list[str],
    extract_image_block_to_payload: bool,
    tmpdir: str,
):
    extracted_elements: list[list[Element]] = []
    for el_type in extract_image_block_types:
        extracted_elements_by_type: list[Element] = []
        for el in elements:
            if el.category == el_type:
                extracted_elements_by_type.append(el)
        extracted_elements.append(extracted_elements_by_type)

    for extracted_elements_by_type in extracted_elements:
        for i, el in enumerate(extracted_elements_by_type):
            if extract_image_block_to_payload:
                assert el.metadata.image_base64 is not None
                assert el.metadata.image_mime_type == "image/jpeg"
                image_data = base64.b64decode(el.metadata.image_base64)
                assert isinstance(image_data, bytes)
                assert el.metadata.image_path is None
            else:
                basename = "table" if el.category == ElementType.TABLE else "figure"
                expected_image_path = os.path.join(
                    str(tmpdir), f"{basename}-{el.metadata.page_number}-{i + 1}.jpg"
                )
                assert el.metadata.image_path == expected_image_path
                assert os.path.isfile(expected_image_path)
                assert el.metadata.image_base64 is None
                assert el.metadata.image_mime_type is None


@pytest.mark.parametrize("file_mode", ["filename", "rb"])
@pytest.mark.parametrize("extract_image_block_to_payload", [False, True])
def test_partition_pdf_element_extraction(
    file_mode,
    extract_image_block_to_payload,
    filename=example_doc_path("pdf/embedded-images-tables.pdf"),
):
    extract_image_block_types = ["Image", "Table"]

    with tempfile.TemporaryDirectory() as tmpdir:
        if file_mode == "filename":
            elements = pdf.partition_pdf(
                filename=filename,
                # Image extraction shouldn't break by setting this
                starting_page_number=20,
                extract_image_block_types=extract_image_block_types,
                extract_image_block_to_payload=extract_image_block_to_payload,
                extract_image_block_output_dir=tmpdir,
            )
        else:
            with open(filename, "rb") as f:
                elements = pdf.partition_pdf(
                    file=f,
                    # Image extraction shouldn't break by setting this
                    starting_page_number=20,
                    extract_image_block_types=extract_image_block_types,
                    extract_image_block_to_payload=extract_image_block_to_payload,
                    extract_image_block_output_dir=tmpdir,
                )
        assert elements[0].metadata.page_number == 20
        assert_element_extraction(
            elements, extract_image_block_types, extract_image_block_to_payload, tmpdir
        )


def test_partition_pdf_always_keep_all_image_elements(
    filename=example_doc_path("pdf/embedded-images.pdf"),
):
    elements = pdf.partition_pdf(
        filename=filename,
        strategy="hi_res",
    )
    image_elements = [el for el in elements if el.category == ElementType.IMAGE]
    assert len(image_elements) == 3


@pytest.fixture()
def expected_element_ids_for_fast_strategy():
    return [
        "27a6cb3e5a4ad399b2f865729bbd3840",
        "a90a54baba0093296a013d26b7acbc17",
        "9be424e2d151dac4b5f36a85e9bbfe65",
        "4631da875fb4996c63b2d80cea6b588e",
        "6264f4eda97a049f4710f9bea0c01cbd",
        "abded7b2ff3a5542c88b4a831755ec24",
        "b781ea5123cb31e0571391b7b42cac75",
        "033f27d2618ba4cda9068b267b5a731e",
        "8982a12fcced30dd12ccbf61d14f30bf",
        "41af2fd5df0cf47aa7e8ecca200d3ac6",
    ]


@pytest.fixture()
def expected_element_ids_for_hi_res_strategy():
    return [
        "27a6cb3e5a4ad399b2f865729bbd3840",
        "a90a54baba0093296a013d26b7acbc17",
        "9be424e2d151dac4b5f36a85e9bbfe65",
        "4631da875fb4996c63b2d80cea6b588e",
        "6264f4eda97a049f4710f9bea0c01cbd",
        "abded7b2ff3a5542c88b4a831755ec24",
        "b781ea5123cb31e0571391b7b42cac75",
        "033f27d2618ba4cda9068b267b5a731e",
        "8982a12fcced30dd12ccbf61d14f30bf",
        "41af2fd5df0cf47aa7e8ecca200d3ac6",
    ]


@pytest.fixture()
def expected_element_ids_for_ocr_strategy():
    return [
        "272ab65cbe81795161128aea59599d83",
        "b38affd7bbbb3dddf5c85ba8b14d380d",
        "65903214d456b8b3cba6faa6714bd9ba",
        "5b41ceae05dcfaeeac32ff8e82dc2ff1",
        "6582fc6c6c595225feeddcc3263f0ae3",
        "64b610c8f4274f1ce2175bf30814409d",
        "8edde8bf2d3a68370dc4bd142c408ca4",
        "a052bc17696043efce2e4f4f28393a83",
    ]


@pytest.fixture()
def expected_ids(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize(
    ("strategy", "expected_ids"),
    [
        (PartitionStrategy.FAST, "expected_element_ids_for_fast_strategy"),
        (PartitionStrategy.HI_RES, "expected_element_ids_for_hi_res_strategy"),
        (PartitionStrategy.OCR_ONLY, "expected_element_ids_for_ocr_strategy"),
    ],
    indirect=["expected_ids"],
)
def test_unique_and_deterministic_element_ids(strategy, expected_ids):
    elements = pdf.partition_pdf(
        example_doc_path("pdf/fake-memo-with-duplicate-page.pdf"),
        strategy=strategy,
        starting_page_number=2,
    )
    ids = [element.id for element in elements]
    assert ids == expected_ids, "Element IDs do not match expected IDs"


@pytest.mark.parametrize("is_path", [True, False])
@pytest.mark.parametrize(
    ("example_doc", "doc_pages"),
    [
        ("pdf/layout-parser-paper-fast.pdf", 2),
        ("img/DA-1p.png", 1),
    ],
)
def test_analysis_artifacts_saved(is_path: bool, example_doc: str, doc_pages: int):
    with tempfile.TemporaryDirectory() as temp_dir:
        file = None
        filename = example_doc_path(example_doc)
        is_image = not Path(filename).suffix.endswith("pdf")
        if not is_path:
            file = open(filename, "rb")  # noqa: SIM115
            filename = None
        pdf.partition_pdf(
            filename=filename,
            file=file,
            is_image=is_image,
            strategy=PartitionStrategy.HI_RES,
            analysis=True,
            analyzed_image_output_dir_path=temp_dir,
        )

        analysis_dir = Path(temp_dir)
        file_analysis_root = None
        if is_path:
            file_analysis_root = analysis_dir / "analysis" / Path(example_doc).stem
        else:
            # if file is not a path, the filename is None and the analysis directory
            # for the document is generated
            generated_file_stem_path = list((analysis_dir / "analysis").iterdir())[0]
            if is_image:
                assert "image" in generated_file_stem_path.name
            else:
                assert "pdf" in generated_file_stem_path.name
            file_analysis_root = generated_file_stem_path
        layout_dump_dir = file_analysis_root / "layout_dump"
        assert layout_dump_dir.exists()
        layout_dump_files = list(layout_dump_dir.iterdir())

        expected_layout_dumps = ["object_detection", "ocr", "pdfminer", "final"]
        assert len(layout_dump_files) == len(expected_layout_dumps)

        for expected_layout_dump in expected_layout_dumps:
            assert (layout_dump_dir / f"{expected_layout_dump}.json").exists()

        bboxes_dir = file_analysis_root / "bboxes"
        assert bboxes_dir.exists()
        bboxes_files = list(bboxes_dir.iterdir())

        expected_renders = ["od_model", "ocr", "pdfminer", "final"]
        assert len(bboxes_files) == doc_pages * len(expected_renders)

        expected_pages = range(1, doc_pages + 1)
        for el in expected_renders:
            for page in expected_pages:
                assert bboxes_dir / f"page{page}_layout_{el}.png" in bboxes_files
        if file:
            file.close()


@pytest.mark.parametrize(
    ("filename", "pdf_hi_res_max_pages", "expected_error"),
    [
        ("pdf/layout-parser-paper-with-empty-pages.pdf", None, False),
        ("pdf/layout-parser-paper-with-empty-pages.pdf", 3, True),
        ("pdf/reliance.pdf", 3, False),
        ("pdf/reliance.pdf", 2, True),
        ("img/DA-1p.jpg", None, False),
        ("img/DA-1p.jpg", 2, False),
    ],
)
def test_pdf_hi_res_max_pages_argument(filename, pdf_hi_res_max_pages, expected_error):
    is_image = not Path(filename).suffix.endswith("pdf")
    if not expected_error:
        pdf.partition_pdf_or_image(
            filename=example_doc_path(filename),
            strategy=PartitionStrategy.HI_RES,
            pdf_hi_res_max_pages=pdf_hi_res_max_pages,
            is_image=is_image,
        )

    else:
        with pytest.raises(PageCountExceededError):
            pdf.partition_pdf_or_image(
                filename=example_doc_path(filename),
                strategy=PartitionStrategy.HI_RES,
                pdf_hi_res_max_pages=pdf_hi_res_max_pages,
                is_image=is_image,
            )


def test_document_to_element_list_omits_coord_system_when_coord_points_absent():
    # TODO (yao): investigate why we need this test. The LayoutElement definition suggests bbox
    # can't be None and it has to be a Rectangle object that has x1, y1, x2, y2 attributes.
    layout_elem_absent_coordinates = MockSinglePageDocumentLayout()
    for page in layout_elem_absent_coordinates.pages:
        for el in page.elements:
            el.bbox = None
    elements = pdf.document_to_element_list(layout_elem_absent_coordinates)
    assert elements[0].metadata.coordinates is None


@dataclass
class MockImage:
    width = 640
    height = 480
    format = "JPG"


@pytest.mark.skip(reason="no current layout model supports parent assignment")
def test_document_to_element_list_handles_parent():
    block1 = LayoutElement.from_coords(1, 2, 3, 4, text="block 1", type="NarrativeText")
    block2 = LayoutElement.from_coords(
        1,
        2,
        3,
        4,
        text="block 2",
        parent=block1,
        type="NarrativeText",
    )
    page = PageLayout(
        number=1,
        image=MockImage(),
    )
    page.elements_array = layout.LayoutElements.from_list([block1, block2])
    doc = DocumentLayout.from_pages([page])
    el1, el2 = pdf.document_to_element_list(doc)
    assert el2.metadata.parent_id == el1.id


@pytest.mark.parametrize(
    ("sort_mode", "call_count"),
    [(SORT_MODE_DONT, 0), (SORT_MODE_BASIC, 1), (SORT_MODE_XY_CUT, 1)],
)
def test_document_to_element_list_doesnt_sort_on_sort_method(sort_mode, call_count):
    block1 = LayoutElement.from_coords(1, 2, 3, 4, text="block 1", type="NarrativeText")
    block2 = LayoutElement.from_coords(
        1,
        2,
        3,
        4,
        text="block 2",
        parent=block1,
        type="NarrativeText",
    )
    page = PageLayout(
        number=1,
        image=MockImage(),
    )
    page.elements_array = layout.LayoutElements.from_list([block1, block2])
    doc = DocumentLayout.from_pages([page])
    with mock.patch.object(pdf, "sort_page_elements") as mock_sort_page_elements:
        pdf.document_to_element_list(doc, sortable=True, sort_mode=sort_mode)
    assert mock_sort_page_elements.call_count == call_count


def test_document_to_element_list_sets_category_depth_titles():
    layout_with_hierarchies = MockSinglePageDocumentLayout()
    elements = pdf.document_to_element_list(layout_with_hierarchies)
    assert elements[0].metadata.category_depth == 1
    assert elements[1].metadata.category_depth == 2
    assert elements[2].metadata.category_depth is None
    assert elements[3].metadata.category_depth == 0
