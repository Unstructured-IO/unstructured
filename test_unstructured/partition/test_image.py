from unittest import mock

import pytest
import requests
from pytesseract import TesseractError
from unstructured_inference.inference import layout

from unstructured.partition import image, pdf


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


def test_partition_image_api(monkeypatch, filename="example-docs/example.jpg"):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    partition_image_response = pdf._partition_via_api(filename)
    assert partition_image_response[0]["type"] == "Title"
    assert partition_image_response[0]["text"] == "Charlie Brown and the Great Pumpkin"
    assert partition_image_response[1]["type"] == "Title"
    assert partition_image_response[1]["text"] == "A Charlie Brown Christmas"


def test_partition_image_api_page_break(monkeypatch, filename="example-docs/example.jpg"):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    partition_image_response = pdf._partition_via_api(filename, include_page_breaks=True)
    assert partition_image_response[0]["type"] == "Title"
    assert partition_image_response[0]["text"] == "Charlie Brown and the Great Pumpkin"
    assert partition_image_response[1]["type"] == "PageBreak"
    assert partition_image_response[2]["type"] == "Title"
    assert partition_image_response[2]["text"] == "A Charlie Brown Christmas"


@pytest.mark.parametrize(
    ("filename", "file"),
    [("example-docs/example.jpg", None), (None, b"0000")],
)
def test_partition_image_local(monkeypatch, filename, file):
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

    partition_image_response = pdf._partition_pdf_or_image_local(filename, file, is_image=True)
    assert partition_image_response[0].type == "Title"
    assert partition_image_response[0].text == "Charlie Brown and the Great Pumpkin"


@pytest.mark.skip("Needs to be fixed upstream in unstructured-inference")
def test_partition_image_local_raises_with_no_filename():
    with pytest.raises(FileNotFoundError):
        pdf._partition_pdf_or_image_local(filename="", file=None, is_image=True)


def test_partition_image_api_raises_with_failed_healthcheck(
    monkeypatch,
    filename="example-docs/example.jpg",
):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_unhealthy_get)

    with pytest.raises(ValueError):
        pdf._partition_via_api(filename=filename, url="http://ml.unstructured.io/layout/image")


def test_partition_image_api_raises_with_failed_api_call(
    monkeypatch,
    filename="example-docs/example.jpg",
):
    monkeypatch.setattr(requests, "post", mock_unsuccessful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    with pytest.raises(ValueError):
        pdf._partition_via_api(filename=filename, url="http://ml.unstructured.io/layout/image")


@pytest.mark.parametrize(
    ("url", "api_called", "local_called"),
    [("fakeurl", True, False), (None, False, True)],
)
def test_partition_image(url, api_called, local_called):
    with mock.patch.object(
        pdf,
        attribute="_partition_via_api",
        new=mock.MagicMock(),
    ), mock.patch.object(pdf, "_partition_pdf_or_image_local", mock.MagicMock()):
        image.partition_image(filename="fake.pdf", url=url)
        assert pdf._partition_via_api.called == api_called
        assert pdf._partition_pdf_or_image_local.called == local_called


def test_partition_image_with_language_passed(filename="example-docs/example.jpg"):
    with mock.patch.object(layout, "process_file_with_model", mock.MagicMock()) as mock_partition:
        image.partition_image(filename=filename, ocr_languages="eng+swe")

    assert mock_partition.call_args.kwargs.get("ocr_languages") == "eng+swe"


def test_partition_image_from_file_with_language_passed(filename="example-docs/example.jpg"):
    with mock.patch.object(layout, "process_data_with_model", mock.MagicMock()) as mock_partition:
        with open(filename, "rb") as f:
            image.partition_image(file=f, ocr_languages="eng+swe")

    assert mock_partition.call_args.kwargs.get("ocr_languages") == "eng+swe"


def test_partition_image_raises_with_invalid_language(filename="example-docs/example.jpg"):
    with pytest.raises(TesseractError):
        image.partition_image(filename=filename, ocr_languages="fakeroo")
