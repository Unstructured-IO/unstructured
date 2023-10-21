import os
from tempfile import SpooledTemporaryFile
from unittest import mock

import pytest
from PIL import Image
from unstructured_inference.inference import layout

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import (
    CoordinatesMetadata,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.partition import ocr, pdf, strategies
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA


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

    @property
    def elements(self):
        return [
            layout.LayoutElement.from_coords(
                type="Title",
                x1=0,
                y1=0,
                x2=2,
                y2=2,
                text="Charlie Brown and the Great Pumpkin",
            ),
        ]


class MockDocumentLayout(layout.DocumentLayout):
    @property
    def pages(self):
        return [
            MockPageLayout(number=0, image=Image.new("1", (1, 1))),
            MockPageLayout(number=1, image=Image.new("1", (1, 1))),
        ]


@pytest.mark.parametrize(
    ("filename", "file"),
    [
        ("example-docs/layout-parser-paper-fast.pdf", None),
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
        ocr,
        "process_data_with_ocr",
        lambda *args, **kwargs: MockDocumentLayout(),
    )
    monkeypatch.setattr(
        ocr,
        "process_data_with_ocr",
        lambda *args, **kwargs: MockDocumentLayout(),
    )

    partition_pdf_response = pdf._partition_pdf_or_image_local(filename, file)
    assert partition_pdf_response[0].text == "Charlie Brown and the Great Pumpkin"


def test_partition_pdf_local_raises_with_no_filename():
    with pytest.raises(FileNotFoundError):
        pdf._partition_pdf_or_image_local(filename="", file=None, is_image=False)


@pytest.mark.parametrize("file_mode", ["filename", "rb", "spool"])
@pytest.mark.parametrize(
    ("strategy", "expected", "origin"),
    # fast: can't capture the "intentionally left blank page" page
    # others: will ignore the actual blank page
    [("fast", {1, 4}, "pdfminer"), ("hi_res", {1, 3, 4}, "pdf"), ("ocr_only", {1, 3, 4}, "OCR")],
)
def test_partition_pdf(
    file_mode,
    strategy,
    expected,
    origin,
    filename="example-docs/layout-parser-paper-with-empty-pages.pdf",
):
    # Test that the partition_pdf function can handle filename
    def _test(result):
        # validate that the result is a non-empty list of dicts
        assert len(result) > 10
        # check that the pdf has multiple different page numbers
        assert {element.metadata.page_number for element in result} == expected
        if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
            assert {element.metadata.detection_origin for element in result} == {origin}

    if file_mode == "filename":
        result = pdf.partition_pdf(filename=filename, strategy=strategy)
        _test(result)
    elif file_mode == "rb":
        with open(filename, "rb") as f:
            result = pdf.partition_pdf(file=f, strategy=strategy)
            _test(result)
    else:
        with open(filename, "rb") as test_file:
            spooled_temp_file = SpooledTemporaryFile()
            spooled_temp_file.write(test_file.read())
            spooled_temp_file.seek(0)
            result = pdf.partition_pdf(file=spooled_temp_file, strategy=strategy)
            _test(result)


@mock.patch.dict(os.environ, {"UNSTRUCTURED_HI_RES_MODEL_NAME": "checkbox"})
def test_partition_pdf_with_model_name_env_var(
    monkeypatch,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])
    with mock.patch.object(
        layout,
        "process_file_with_model",
        mock.MagicMock(),
    ) as mock_process:
        pdf.partition_pdf(filename=filename, strategy="hi_res")
        mock_process.assert_called_once_with(
            filename,
            is_image=False,
            pdf_image_dpi=200,
            model_name="checkbox",
        )


def test_partition_pdf_with_model_name(
    monkeypatch,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])
    with mock.patch.object(
        layout,
        "process_file_with_model",
        mock.MagicMock(),
    ) as mock_process:
        pdf.partition_pdf(filename=filename, strategy="hi_res", model_name="checkbox")
        mock_process.assert_called_once_with(
            filename,
            is_image=False,
            pdf_image_dpi=200,
            model_name="checkbox",
        )


def test_partition_pdf_with_auto_strategy(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(filename=filename, strategy="auto")
    title = "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis"
    assert elements[6].text == title
    assert elements[6].metadata.filename == "layout-parser-paper-fast.pdf"
    assert elements[6].metadata.file_directory == "example-docs"


def test_partition_pdf_with_page_breaks(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(filename=filename, url=None, include_page_breaks=True)
    assert "PageBreak" in [elem.category for elem in elements]


def test_partition_pdf_with_no_page_breaks(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(filename=filename, url=None)
    assert "PageBreak" not in [elem.category for elem in elements]


def test_partition_pdf_with_fast_strategy(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(filename=filename, url=None, strategy="fast")
    assert len(elements) > 10
    # check that the pdf has multiple different page numbers
    assert {element.metadata.page_number for element in elements} == {1, 2}
    for element in elements:
        assert element.metadata.filename == "layout-parser-paper-fast.pdf"


def test_partition_pdf_with_fast_neg_coordinates():
    filename = "example-docs/negative-coords.pdf"
    elements = pdf.partition_pdf(filename=filename, url=None, strategy="fast")
    assert len(elements) == 5
    assert elements[0].metadata.coordinates.points[0][0] < 0
    assert elements[0].metadata.coordinates.points[1][0] < 0


def test_partition_pdf_with_fast_groups_text(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(filename=filename, url=None, strategy="fast")

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
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(file=f, url=None, strategy="fast")
    assert len(elements) > 10


def test_partition_pdf_with_fast_strategy_and_page_breaks(
    caplog,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(
        filename=filename,
        url=None,
        strategy="fast",
        include_page_breaks=True,
    )
    assert len(elements) > 10
    assert "PageBreak" in [elem.category for elem in elements]

    assert "unstructured_inference is not installed" not in caplog.text
    for element in elements:
        assert element.metadata.filename == "layout-parser-paper-fast.pdf"


def test_partition_pdf_raises_with_bad_strategy(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    with pytest.raises(ValueError):
        pdf.partition_pdf(filename=filename, url=None, strategy="made_up")


def test_partition_pdf_falls_back_to_fast(
    monkeypatch,
    caplog,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    def mock_exists(dep):
        return dep not in ["unstructured_inference", "pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)

    mock_return = [Text("Hello there!")]
    with mock.patch.object(
        pdf,
        "extractable_elements",
        return_value=mock_return,
    ) as mock_partition:
        pdf.partition_pdf(filename=filename, url=None, strategy="hi_res")

    mock_partition.assert_called_once()
    assert "unstructured_inference is not installed" in caplog.text


def test_partition_pdf_falls_back_to_fast_from_ocr_only(
    monkeypatch,
    caplog,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    def mock_exists(dep):
        return dep not in ["pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)

    mock_return = [Text("Hello there!")]
    with mock.patch.object(
        pdf,
        "extractable_elements",
        return_value=mock_return,
    ) as mock_partition, mock.patch.object(
        pdf,
        "_partition_pdf_or_image_with_ocr",
    ) as mock_partition_ocr:
        pdf.partition_pdf(filename=filename, url=None, strategy="ocr_only")

    mock_partition.assert_called_once()
    mock_partition_ocr.assert_not_called()
    assert "pytesseract is not installed" in caplog.text


def test_partition_pdf_falls_back_to_hi_res_from_ocr_only(
    monkeypatch,
    caplog,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    def mock_exists(dep):
        return dep not in ["pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])

    mock_return = [Text("Hello there!")]
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_local",
        return_value=mock_return,
    ) as mock_partition:
        pdf.partition_pdf(filename=filename, url=None, strategy="ocr_only")

    mock_partition.assert_called_once()
    assert "pytesseract is not installed" in caplog.text


def test_partition_pdf_falls_back_to_ocr_only(
    monkeypatch,
    caplog,
    filename="example-docs/layout-parser-paper-fast.pdf",
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
        pdf.partition_pdf(filename=filename, url=None, strategy="hi_res")

    mock_partition.assert_called_once()
    assert "unstructured_inference is not installed" in caplog.text


def test_partition_pdf_uses_table_extraction():
    filename = "example-docs/layout-parser-paper-fast.pdf"
    with mock.patch(
        "unstructured.partition.ocr.process_file_with_ocr",
    ) as mock_process_file_with_model:
        pdf.partition_pdf(filename, infer_table_structure=True)
        assert mock_process_file_with_model.call_args[1]["infer_table_structure"]


@pytest.mark.parametrize(
    ("ocr_mode"),
    [
        ("entire_page"),
        ("individual_blocks"),
    ],
)
def test_partition_pdf_hi_table_extraction_with_languages(ocr_mode):
    filename = "example-docs/korean-text-with-tables.pdf"
    elements = pdf.partition_pdf(
        filename=filename,
        ocr_mode=ocr_mode,
        languages=["kor"],
        strategy="hi_res",
        infer_table_structure=True,
    )
    table = [el.metadata.text_as_html for el in elements if el.metadata.text_as_html]
    assert len(table) == 2
    assert "<table><thead><th>" in table[0]
    # FIXME(yuming): didn't test full sentence here since unit test and docker test have
    # some differences on spaces between characters
    assert "업" in table[0]


def test_partition_pdf_with_copy_protection():
    filename = os.path.join("example-docs", "copy-protected.pdf")
    elements = pdf.partition_pdf(filename=filename, strategy="hi_res")
    title = "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis"
    idx = 3
    assert elements[idx].text == title
    assert {element.metadata.page_number for element in elements} == {1, 2}
    assert elements[idx].metadata.detection_class_prob is not None
    assert isinstance(elements[idx].metadata.detection_class_prob, float)


def test_partition_pdf_with_dpi():
    filename = os.path.join("example-docs", "copy-protected.pdf")
    with mock.patch.object(layout, "process_file_with_model", mock.MagicMock()) as mock_process:
        pdf.partition_pdf(filename=filename, strategy="hi_res", pdf_image_dpi=100)
        mock_process.assert_called_once_with(
            filename,
            is_image=False,
            model_name=pdf.default_hi_res_model(),
            pdf_image_dpi=100,
        )


def test_partition_pdf_requiring_recursive_text_grab(filename="example-docs/reliance.pdf"):
    elements = pdf.partition_pdf(filename=filename, strategy="fast")
    assert len(elements) > 50
    assert elements[0].metadata.page_number == 1
    assert elements[-1].metadata.page_number == 3


def test_partition_pdf_with_copy_protection_fallback_to_hi_res(caplog):
    filename = os.path.join("example-docs", "loremipsum-flat.pdf")
    elements = pdf.partition_pdf(filename=filename, strategy="fast")
    elements[0] == Title(
        "LayoutParser: A Uniﬁed Toolkit for Deep Based Document Image Analysis",
    )
    assert "PDF text is not extractable" in caplog.text


def test_partition_pdf_fails_if_pdf_not_processable(
    monkeypatch,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    def mock_exists(dep):
        return dep not in ["unstructured_inference", "pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])

    with pytest.raises(ValueError):
        pdf.partition_pdf(filename=filename)


def test_partition_pdf_fast_groups_text_in_text_box():
    filename = os.path.join("example-docs", "chevron-page.pdf")
    elements = pdf.partition_pdf(filename=filename, strategy="fast")
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
    filename="example-docs/layout-parser-paper-fast.pdf",
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
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(
            file=f,
            url=None,
            strategy="fast",
            metadata_filename="test",
        )
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_pdf_with_auto_strategy_exclude_metadata(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(
        filename=filename,
        strategy="auto",
        include_metadata=False,
    )
    title = "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis"
    assert elements[6].text == title
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_pdf_with_fast_strategy_from_file_exclude_metadata(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(
            file=f,
            url=None,
            strategy="fast",
            include_metadata=False,
        )
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_pdf_with_auto_strategy_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = pdf.partition_pdf(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_pdf_with_auto_strategy_custom_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = pdf.partition_pdf(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_pdf_with_orc_only_strategy_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = pdf.partition_pdf(filename=filename, strategy="ocr_only")

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_pdf_with_ocr_only_strategy_custom_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = pdf.partition_pdf(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
        strategy="ocr_only",
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_pdf_with_hi_res_strategy_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = pdf.partition_pdf(filename=filename, strategy="hi_res")

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_pdf_with_hi_res_strategy_custom_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = pdf.partition_pdf(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
        strategy="hi_res",
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_pdf_from_file_with_auto_strategy_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(
            file=f,
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_pdf_from_file_with_auto_strategy_custom_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(
            file=f,
            metadata_last_modified=expected_last_modification_date,
        )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_pdf_from_file_with_ocr_only_strategy_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(file=f, strategy="ocr_only")

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_pdf_from_file_with_ocr_only_strategy_custom_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(
            file=f,
            metadata_last_modified=expected_last_modification_date,
            strategy="ocr_only",
        )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_pdf_from_file_with_hi_res_strategy_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(file=f, strategy="hi_res")

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_pdf_from_file_with_hi_res_strategy_custom_metadata_date(
    mocker,
    filename="example-docs/copy-protected.pdf",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(
            file=f,
            metadata_last_modified=expected_last_modification_date,
            strategy="hi_res",
        )

    assert elements[0].metadata.last_modified == expected_last_modification_date


@pytest.mark.parametrize("strategy", ["fast", "hi_res"])
def test_partition_pdf_with_json(strategy: str):
    elements = pdf.partition_pdf(
        example_doc_path("layout-parser-paper-fast.pdf"),
        strategy=strategy,
    )
    assert_round_trips_through_JSON(elements)


def test_partition_pdf_with_ocr_has_coordinates_from_filename(
    filename="example-docs/chevron-page.pdf",
):
    elements = pdf.partition_pdf(filename=filename, strategy="ocr_only")
    assert elements[0].metadata.coordinates.points == (
        (657.0, 2144.0),
        (657.0, 2106.0),
        (1043.0, 2106.0),
        (1043.0, 2144.0),
    )


def test_partition_pdf_with_ocr_has_coordinates_from_file(
    filename="example-docs/chevron-page.pdf",
):
    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(
            file=f,
            strategy="ocr_only",
        )
    assert elements[0].metadata.coordinates.points == (
        (657.0, 2144.0),
        (657.0, 2106.0),
        (1043.0, 2106.0),
        (1043.0, 2144.0),
    )


@pytest.mark.parametrize(
    ("filename"),
    [
        ("example-docs/multi-column-2p.pdf"),
        ("example-docs/layout-parser-paper-fast.pdf"),
        ("example-docs/list-item-example.pdf"),
    ],
)
def test_partition_pdf_with_ocr_coordinates_are_not_nan_from_file(
    filename,
):
    import math

    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(
            file=f,
            strategy="ocr_only",
        )
    for element in elements:
        if element.metadata.coordinates:
            for point in element.metadata.coordinates.points:
                if point[0] and point[1]:
                    assert point[0] is not math.nan
                    assert point[1] is not math.nan


def test_add_chunking_strategy_by_title_on_partition_pdf(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(filename=filename)
    chunk_elements = pdf.partition_pdf(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_pdf_formats_languages_for_tesseract():
    filename = "example-docs/DA-1p.pdf"
    with mock.patch.object(ocr, "process_file_with_ocr", mock.MagicMock()) as mock_process:
        pdf.partition_pdf(filename=filename, strategy="hi_res", languages=["en"])
        assert mock_process.call_args[1]["ocr_languages"] == "eng"


def test_partition_pdf_warns_with_ocr_languages(caplog):
    filename = "example-docs/chevron-page.pdf"
    pdf.partition_pdf(filename=filename, strategy="hi_res", ocr_languages="eng")
    assert "The ocr_languages kwarg will be deprecated" in caplog.text


def test_partition_pdf_or_image_warns_with_ocr_languages(caplog):
    filename = "example-docs/DA-1p.pdf"
    pdf.partition_pdf_or_image(filename=filename, strategy="hi_res", ocr_languages="eng")
    assert "The ocr_languages kwarg will be deprecated" in caplog.text


def test_partition_categorization_backup():
    text = "This is Clearly a Title"
    with mock.patch.object(pdf, "_partition_pdf_or_image_local", return_value=[Text(text)]):
        elements = pdf.partition_pdf_or_image(
            "example-docs/layout-parser-paper-fast.pdf",
            strategy="hi_res",
        )
        # Should have changed the element class from Text to Title
        assert isinstance(elements[0], Title)
        assert elements[0].text == text


@pytest.mark.parametrize(
    "filename",
    ["example-docs/layout-parser-paper-fast.pdf"],
)
def test_combine_numbered_list(filename):
    elements = pdf.partition_pdf(filename=filename, strategy="auto")
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
    "filename",
    ["example-docs/layout-parser-paper-fast.pdf"],
)
def test_partition_pdf_hyperlinks(filename):
    elements = pdf.partition_pdf(filename=filename, strategy="auto")
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
    "filename",
    ["example-docs/embedded-link.pdf"],
)
def test_partition_pdf_hyperlinks_multiple_lines(filename):
    elements = pdf.partition_pdf(filename=filename, strategy="auto")
    assert elements[-1].metadata.links[-1]["text"] == "capturing"
    assert len(elements[-1].metadata.links) == 2


def test_partition_pdf_uses_model_name():
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_local",
    ) as mockpartition:
        pdf.partition_pdf(
            "example-docs/layout-parser-paper-fast.pdf",
            model_name="test",
            strategy="hi_res",
        )

        mockpartition.assert_called_once()
        assert "model_name" in mockpartition.call_args.kwargs
        assert mockpartition.call_args.kwargs["model_name"]


def test_partition_pdf_word_bbox_not_char(
    filename="example-docs/interface-config-guide-p93.pdf",
):
    try:
        elements = pdf.partition_pdf(filename=filename)
    except Exception as e:
        raise ("Partitioning fail: %s" % e)
    assert len(elements) == 17


def test_partition_pdf_raises_TypeError_for_invalid_languages():
    filename = "example-docs/chevron-page.pdf"
    with pytest.raises(TypeError):
        pdf.partition_pdf(filename=filename, strategy="hi_res", languages="eng")


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


@pytest.fixture(scope="session")
def chipper_results():
    elements = pdf.partition_pdf(
        "example-docs/layout-parser-paper-fast.pdf",
        strategy="hi_res",
        model_name="chipper",
    )
    return elements


@pytest.fixture(scope="session")
def chipper_children(chipper_results):
    return [el for el in chipper_results if el.metadata.parent_id is not None]


def test_chipper_has_hierarchy(chipper_children):
    assert chipper_children


def test_chipper_not_losing_parents(chipper_results, chipper_children):
    assert all(
        [el for el in chipper_results if el.id == child.metadata.parent_id]
        for child in chipper_children
    )


def test_partition_model_name_default_to_None():
    filename = "example-docs/DA-1p.pdf"
    try:
        pdf.partition_pdf(
            filename=filename,
            strategy="hi_res",
            ocr_languages="eng",
            model_name=None,
        )
    except AttributeError:
        pytest.fail("partition_pdf() raised AttributeError unexpectedly!")
