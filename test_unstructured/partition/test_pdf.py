import pytest

import requests

import unstructured.partition.pdf as pdf


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
            }
        ]
    }
    return MockResponse(status_code=200, response=response)


def test_partition_pdf(monkeypatch, filename="example-docs/layout-parser-paper-fast.pdf"):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    partition_pdf_response = pdf.partition_pdf(filename)
    assert partition_pdf_response[0]["type"] == "Title"
    assert partition_pdf_response[0]["text"] == "Charlie Brown and the Great Pumpkin"


def test_partition_pdf_raises_with_no_filename(
    monkeypatch, filename="example-docs/layout-parser-paper-fast.pdf"
):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    with pytest.raises(FileNotFoundError):
        pdf.partition_pdf(filename=None, file=None)


def test_partition_pdf_raises_with_failed_healthcheck(
    monkeypatch, filename="example-docs/layout-parser-paper-fast.pdf"
):
    monkeypatch.setattr(requests, "post", mock_successful_post)
    monkeypatch.setattr(requests, "get", mock_unhealthy_get)

    with pytest.raises(ValueError):
        pdf.partition_pdf(filename=filename)


def test_partition_pdf_raises_with_failed_api_call(
    monkeypatch, filename="example-docs/layout-parser-paper-fast.pdf"
):
    monkeypatch.setattr(requests, "post", mock_unsuccessful_post)
    monkeypatch.setattr(requests, "get", mock_healthy_get)

    with pytest.raises(ValueError):
        pdf.partition_pdf(filename=filename)
