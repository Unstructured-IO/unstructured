import os
from unittest import mock

import pytest
import requests
from unstructured_inference.inference import layout

from unstructured.documents.elements import NarrativeText, PageBreak, Text, Title
from unstructured.partition import pdf


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
    assert partition_pdf_response[0].type == "Title"
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
    monkeypatch.setattr(pdf, "is_pdf_text_extractable", lambda *args, **kwargs: True)
    with mock.patch.object(
        pdf,
        attribute="_partition_via_api",
        new=mock.MagicMock(),
    ), mock.patch.object(pdf, "_partition_pdf_or_image_local", mock.MagicMock()):
        pdf.partition_pdf(filename="fake.pdf", url=url)
        assert pdf._partition_via_api.called == api_called
        assert pdf._partition_pdf_or_image_local.called == local_called


@pytest.mark.parametrize(
    ("url", "api_called", "local_called"),
    [("fakeurl", True, False), (None, False, True)],
)
def test_partition_pdf_with_template(url, api_called, local_called, monkeypatch):
    monkeypatch.setattr(pdf, "is_pdf_text_extractable", lambda *args, **kwargs: True)
    with mock.patch.object(
        pdf,
        attribute="_partition_via_api",
        new=mock.MagicMock(),
    ), mock.patch.object(pdf, "_partition_pdf_or_image_local", mock.MagicMock()):
        pdf.partition_pdf(filename="fake.pdf", url=url, template="checkbox")
        assert pdf._partition_via_api.called == api_called
        assert pdf._partition_pdf_or_image_local.called == local_called


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
    monkeypatch.setattr(pdf, "dependency_exists", lambda dep: dep != "detectron2")

    mock_return = [Text("Hello there!")]
    with mock.patch.object(
        pdf,
        "_partition_pdf_with_pdfminer",
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


@pytest.mark.parametrize(
    ("filename", "from_file", "expected"),
    [
        ("layout-parser-paper-fast.pdf", True, True),
        ("copy-protected.pdf", True, False),
        ("layout-parser-paper-fast.pdf", False, True),
        ("copy-protected.pdf", False, False),
    ],
)
def test_is_pdf_text_extractable(filename, from_file, expected):
    filename = os.path.join("example-docs", filename)

    if from_file:
        with open(filename, "rb") as f:
            extractable = pdf.is_pdf_text_extractable(file=f)
    else:
        extractable = pdf.is_pdf_text_extractable(filename=filename)

    assert extractable is expected


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
    monkeypatch.setattr(pdf, "dependency_exists", lambda dep: dep != "detectron2")
    monkeypatch.setattr(pdf, "is_pdf_text_extractable", lambda *args, **kwargs: False)

    with pytest.raises(ValueError):
        pdf.partition_pdf(filename=filename)
