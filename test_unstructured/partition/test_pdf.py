import os
from tempfile import SpooledTemporaryFile
from unittest import mock

import pytest
import requests
from unstructured_inference.inference import layout

from unstructured.documents.elements import NarrativeText, PageBreak, Text, Title
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
                "elements": [{"type": "Title", "text": "Charlie Brown and the Great Pumpkin"}],
            },
            {
                "number": 1,
                "elements": [{"type": "Title", "text": "A Charlie Brown Christmas"}],
            },
        ],
    }
    return MockResponse(status_code=200, response=response)


class MockPageLayout(layout.PageLayout):
    def __init__(self, number: int):
        pass

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
            MockPageLayout(
                number=0,
            ),
        ]


def test_partition_pdf_api(monkeypatch, filename="example-docs/layout-parser-paper-fast.pdf"):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    partition_pdf_response = pdf._partition_via_api(filename)
    assert partition_pdf_response[0]["type"] == "Title"
    assert partition_pdf_response[0]["text"] == "Charlie Brown and the Great Pumpkin"
    assert partition_pdf_response[1]["type"] == "Title"
    assert partition_pdf_response[1]["text"] == "A Charlie Brown Christmas"


def test_partition_pdf_api_page_breaks(
    monkeypatch,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    partition_pdf_response = pdf._partition_via_api(filename, include_page_breaks=True)
    assert partition_pdf_response[0]["type"] == "Title"
    assert partition_pdf_response[0]["text"] == "Charlie Brown and the Great Pumpkin"
    assert partition_pdf_response[1]["type"] == "PageBreak"
    assert partition_pdf_response[2]["type"] == "Title"
    assert partition_pdf_response[2]["text"] == "A Charlie Brown Christmas"


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


def test_partition_pdf_api_raises_with_no_filename(monkeypatch):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    with pytest.raises(FileNotFoundError):
        pdf._partition_via_api(filename=None, file=None)


def test_partition_pdf_local_raises_with_no_filename():
    with pytest.raises(FileNotFoundError):
        pdf._partition_pdf_or_image_local(filename="", file=None, is_image=False)


def test_partition_pdf_api_raises_with_failed_healthcheck(
    monkeypatch,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_unhealthy_get)

    with pytest.raises(ValueError):
        pdf._partition_via_api(filename=filename)


def test_partition_pdf_api_raises_with_failed_api_call(
    monkeypatch,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    monkeypatch.setattr(requests, "post", mock_unsuccessful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    with pytest.raises(ValueError):
        pdf._partition_via_api(filename=filename)


@pytest.mark.parametrize(
    ("url", "api_called", "local_called"),
    [("fakeurl", True, False), (None, False, True)],
)
def test_partition_pdf(url, api_called, local_called, monkeypatch):
    monkeypatch.setattr(strategies, "is_pdf_text_extractable", lambda *args, **kwargs: True)
    with mock.patch.object(
        pdf,
        attribute="_partition_via_api",
        new=mock.MagicMock(),
    ), mock.patch.object(pdf, "_partition_pdf_or_image_local", mock.MagicMock()):
        pdf.partition_pdf(filename="fake.pdf", strategy="hi_res", url=url)
        assert pdf._partition_via_api.called == api_called
        assert pdf._partition_pdf_or_image_local.called == local_called


@pytest.mark.parametrize(
    ("strategy"),
    [("fast"), ("hi_res"), ("ocr_only")],
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


@pytest.mark.parametrize(
    ("url", "api_called", "local_called"),
    [("fakeurl", True, False), (None, False, True)],
)
def test_partition_pdf_with_template(url, api_called, local_called, monkeypatch):
    monkeypatch.setattr(strategies, "is_pdf_text_extractable", lambda *args, **kwargs: True)
    with mock.patch.object(
        pdf,
        attribute="_partition_via_api",
        new=mock.MagicMock(),
    ), mock.patch.object(pdf, "_partition_pdf_or_image_local", mock.MagicMock()):
        pdf.partition_pdf(filename="fake.pdf", strategy="hi_res", url=url, template="checkbox")
        assert pdf._partition_via_api.called == api_called
        assert pdf._partition_pdf_or_image_local.called == local_called


def test_partition_pdf_with_auto_strategy(filename="example-docs/layout-parser-paper-fast.pdf"):
    elements = pdf.partition_pdf(filename=filename, strategy="auto")
    titles = [el for el in elements if el.category == "Title" and len(el.text.split(" ")) > 10]
    title = "LayoutParser: A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis"
    assert titles[0].text == title
    assert titles[0].metadata.filename == "layout-parser-paper-fast.pdf"
    assert titles[0].metadata.file_directory == "example-docs"


def test_partition_pdf_with_page_breaks(filename="example-docs/layout-parser-paper-fast.pdf"):
    elements = pdf.partition_pdf(filename=filename, url=None, include_page_breaks=True)
    assert PageBreak() in elements


def test_partition_pdf_with_no_page_breaks(filename="example-docs/layout-parser-paper-fast.pdf"):
    elements = pdf.partition_pdf(filename=filename, url=None)
    assert PageBreak() not in elements


def test_partition_pdf_with_fast_strategy(filename="example-docs/layout-parser-paper-fast.pdf"):
    elements = pdf.partition_pdf(filename=filename, url=None, strategy="fast")
    assert len(elements) > 10


def test_partition_pdf_with_fast_groups_text(filename="example-docs/layout-parser-paper-fast.pdf"):
    elements = pdf.partition_pdf(filename=filename, url=None, strategy="fast")

    first_narrative_element = None
    for element in elements:
        if isinstance(element, NarrativeText):
            first_narrative_element = element
            break

    assert len(first_narrative_element.text) > 1000
    assert first_narrative_element.text.startswith("Abstract. Recent advances")
    assert first_narrative_element.text.endswith("https://layout-parser.github.io.")


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
    assert PageBreak() in elements

    assert "detectron2 is not installed" not in caplog.text


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
        return dep not in ["detectron2", "pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)

    mock_return = [Text("Hello there!")]
    with mock.patch.object(
        pdf,
        "_partition_pdf_with_pdfminer",
        return_value=mock_return,
    ) as mock_partition:
        pdf.partition_pdf(filename=filename, url=None, strategy="hi_res")

    mock_partition.assert_called_once()
    assert "detectron2 is not installed" in caplog.text


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
        "_partition_pdf_with_pdfminer",
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
    monkeypatch.setattr(strategies, "is_pdf_text_extractable", lambda *args, **kwargs: False)

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
        return dep not in ["detectron2"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)

    mock_return = [Text("Hello there!")]
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_with_ocr",
        return_value=mock_return,
    ) as mock_partition:
        pdf.partition_pdf(filename=filename, url=None, strategy="hi_res")

    mock_partition.assert_called_once()
    assert "detectron2 is not installed" in caplog.text


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


def test_partition_pdf_with_copy_protection_fallback_to_hi_res(caplog):
    filename = os.path.join("example-docs", "copy-protected.pdf")
    elements = pdf.partition_pdf(filename=filename, strategy="fast")
    elements[0] == Title("LayoutParser: A Uniﬁed Toolkit for Deep Based Document Image Analysis")
    assert "PDF text is not extractable" in caplog.text


def test_partition_pdf_fails_if_pdf_not_processable(
    monkeypatch,
    filename="example-docs/layout-parser-paper-fast.pdf",
):
    def mock_exists(dep):
        return dep not in ["detectron2", "pytesseract"]

    monkeypatch.setattr(strategies, "dependency_exists", mock_exists)
    monkeypatch.setattr(strategies, "is_pdf_text_extractable", lambda *args, **kwargs: False)

    with pytest.raises(ValueError):
        pdf.partition_pdf(filename=filename)


def test_partition_pdf_fast_groups_text_in_text_box():
    filename = os.path.join("example-docs", "chevron-page.pdf")
    elements = pdf.partition_pdf(filename=filename, strategy="fast")

    assert elements[0] == Title(
        "eastern mediterranean",
        coordinates=(
            (193.1741, 71.94000000000005),
            (193.1741, 91.94000000000005),
            (418.6881, 91.94000000000005),
            (418.6881, 71.94000000000005),
        ),
    )

    assert isinstance(elements[1], NarrativeText)
    assert str(elements[1]).startswith("We")
    assert str(elements[1]).endswith("Jordan and Egypt.")

    assert elements[3] == Title(
        "kilograms CO₂e/boe carbon intensity from our Eastern Mediterranean operations in 2022",
        coordinates=(
            (69.4871, 222.4357),
            (69.4871, 272.1607),
            (197.8209, 272.1607),
            (197.8209, 222.4357),
        ),
    )
