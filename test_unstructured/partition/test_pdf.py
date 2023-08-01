import os
from tempfile import SpooledTemporaryFile
from unittest import mock

import pytest
from PIL import Image
from unstructured_inference.inference import layout

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import (
    CoordinatesMetadata,
    ElementMetadata,
    NarrativeText,
    Text,
    Title,
)
from unstructured.partition import pdf, strategies


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
            layout.LayoutElement(
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
        ]


@pytest.mark.parametrize(
    ("filename", "file"),
    [("example-docs/layout-parser-paper-fast.pdf", None), (None, b"0000")],
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

    partition_pdf_response = pdf._partition_pdf_or_image_local(filename, file)
    assert partition_pdf_response[0].text == "Charlie Brown and the Great Pumpkin"


def test_partition_pdf_local_raises_with_no_filename():
    with pytest.raises(FileNotFoundError):
        pdf._partition_pdf_or_image_local(filename="", file=None, is_image=False)


@pytest.mark.parametrize(
    "strategy",
    ["fast", "hi_res", "ocr_only"],
)
def test_partition_pdf_with_filename(
    strategy,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    # Test that the partition_pdf function can handle filename
    result = pdf.partition_pdf(filename=filename, strategy=strategy)
    # validate that the result is a non-empty list of dicts
    assert len(result) > 10
    # check that the pdf has multiple different page numbers
    assert {element.metadata.page_number for element in result} == {1, 2}


@pytest.mark.parametrize(
    "strategy",
    ["fast", "hi_res", "ocr_only"],
)
def test_partition_pdf_with_file_rb(
    strategy,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    # Test that the partition_pdf function can handle BufferedReader
    with open(filename, "rb") as f:
        result = pdf.partition_pdf(file=f, strategy=strategy)
        # validate that the result is a non-empty list of dicts
        assert len(result) > 10
        # check that the pdf has multiple different page numbers
        assert {element.metadata.page_number for element in result} == {1, 2}


@pytest.mark.parametrize(
    "strategy",
    ["fast", "hi_res", "ocr_only"],
)
def test_partition_pdf_with_spooled_file(
    strategy,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    # Test that the partition_pdf function can handle a SpooledTemporaryFile
    with open(filename, "rb") as test_file:
        spooled_temp_file = SpooledTemporaryFile()
        spooled_temp_file.write(test_file.read())
        spooled_temp_file.seek(0)
        result = pdf.partition_pdf(file=spooled_temp_file, strategy=strategy)
        # validate that the result is a non-empty list of dicts
        assert len(result) > 10
        # check that the pdf has multiple different page numbers
        assert {element.metadata.page_number for element in result} == {1, 2}


@mock.patch.dict(os.environ, {"UNSTRUCTURED_HI_RES_MODEL_NAME": "checkbox"})
def test_partition_pdf_with_model_name_env_var(
    monkeypatch,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])
    with mock.patch.object(layout, "process_file_with_model", mock.MagicMock()) as mock_process:
        pdf.partition_pdf(filename=filename, strategy="hi_res")
        mock_process.assert_called_once_with(
            filename,
            is_image=False,
            ocr_languages="eng",
            extract_tables=False,
            model_name="checkbox",
        )


def test_partition_pdf_with_model_name(
    monkeypatch,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    monkeypatch.setattr(pdf, "extractable_elements", lambda *args, **kwargs: [])
    with mock.patch.object(layout, "process_file_with_model", mock.MagicMock()) as mock_process:
        pdf.partition_pdf(filename=filename, strategy="hi_res", model_name="checkbox")
        mock_process.assert_called_once_with(
            filename,
            is_image=False,
            ocr_languages="eng",
            extract_tables=False,
            model_name="checkbox",
        )


def test_partition_pdf_with_auto_strategy(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(filename=filename, strategy="auto")
    title = "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis"
    assert elements[0].text == title
    assert elements[0].metadata.filename == "layout-parser-paper-fast.pdf"
    assert elements[0].metadata.file_directory == "example-docs"


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
    ) as mock_partition:
        pdf.partition_pdf(filename=filename, url=None, strategy="ocr_only")

    mock_partition.assert_called_once()
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
        "unstructured_inference.inference.layout.process_file_with_model",
    ) as mock_process_file_with_model:
        pdf.partition_pdf(filename, infer_table_structure=True)
        assert mock_process_file_with_model.call_args[1]["extract_tables"]


def test_partition_pdf_with_copy_protection():
    filename = os.path.join("example-docs", "copy-protected.pdf")
    elements = pdf.partition_pdf(filename=filename, strategy="hi_res")
    elements[0] == Title("LayoutParser: A Uniﬁed Toolkit for Deep Based Document Image Analysis")
    # check that the pdf has multiple different page numbers
    assert {element.metadata.page_number for element in elements} == {1, 2}


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
    assert elements[0] == Title("eastern mediterranean", metadata=expected_elem_metadata_0)
    assert isinstance(elements[1], NarrativeText)
    assert str(elements[1]).startswith("We")
    assert str(elements[1]).endswith("Jordan and Egypt.")

    expected_coordinate_points_3 = (
        (273.9929, 181.16470000000004),
        (273.9929, 226.16470000000004),
        (333.59990000000005, 226.16470000000004),
        (333.59990000000005, 181.16470000000004),
    )
    expected_coordinate_system_3 = PixelSpace(width=612, height=792)
    expected_elem_metadata_3 = ElementMetadata(
        coordinates=CoordinatesMetadata(
            points=expected_coordinate_points_3,
            system=expected_coordinate_system_3,
        ),
    )
    assert elements[3] == Title("1st", metadata=expected_elem_metadata_3)


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
        elements = pdf.partition_pdf(file=f, url=None, strategy="fast", metadata_filename="test")
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_pdf_with_auto_strategy_exclude_metadata(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    elements = pdf.partition_pdf(filename=filename, strategy="auto", include_metadata=False)
    title = "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis"
    assert elements[0].text == title
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_pdf_with_fast_strategy_from_file_exclude_metadata(
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    with open(filename, "rb") as f:
        elements = pdf.partition_pdf(file=f, url=None, strategy="fast", include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}
