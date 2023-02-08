import pytest
import requests
from unittest import mock

from unstructured.documents.elements import PageBreak
import unstructured.partition.pdf as pdf
import unstructured_inference.inference.layout as layout


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
        ]
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
                coordinates=[(0, 0), (2, 2)],
                text="Charlie Brown and the Great Pumpkin",
            )
        ]


class MockDocumentLayout(layout.DocumentLayout):
    @property
    def pages(self):
        return [
            MockPageLayout(
                number=0,
            )
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
    monkeypatch, filename="example-docs/layout-parser-paper-fast.pdf"
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
    "filename, file", [("example-docs/layout-parser-paper-fast.pdf", None), (None, b"0000")]
)
def test_partition_pdf_local(monkeypatch, filename, file):
    monkeypatch.setattr(
        layout, "process_data_with_model", lambda *args, **kwargs: MockDocumentLayout()
    )
    monkeypatch.setattr(
        layout, "process_file_with_model", lambda *args, **kwargs: MockDocumentLayout()
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
    monkeypatch, filename="example-docs/layout-parser-paper-fast.pdf"
):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_unhealthy_get)

    with pytest.raises(ValueError):
        pdf._partition_via_api(filename=filename)


def test_partition_pdf_api_raises_with_failed_api_call(
    monkeypatch, filename="example-docs/layout-parser-paper-fast.pdf"
):
    monkeypatch.setattr(requests, "post", mock_unsuccessful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    with pytest.raises(ValueError):
        pdf._partition_via_api(filename=filename)


@pytest.mark.parametrize(
    "url, api_called, local_called", [("fakeurl", True, False), (None, False, True)]
)
def test_partition_pdf(url, api_called, local_called):
    with mock.patch.object(
        pdf, attribute="_partition_via_api", new=mock.MagicMock()
    ), mock.patch.object(pdf, "_partition_pdf_or_image_local", mock.MagicMock()):
        pdf.partition_pdf(filename="fake.pdf", url=url)
        assert pdf._partition_via_api.called == api_called
        assert pdf._partition_pdf_or_image_local.called == local_called


@pytest.mark.parametrize(
    "url, api_called, local_called", [("fakeurl", True, False), (None, False, True)]
)
def test_partition_pdf_with_template(url, api_called, local_called):
    with mock.patch.object(
        pdf, attribute="_partition_via_api", new=mock.MagicMock()
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
