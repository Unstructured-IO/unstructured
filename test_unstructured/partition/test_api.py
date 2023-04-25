import os
import pathlib

import pytest
import requests

from unstructured.documents.elements import NarrativeText
from unstructured.partition.api import partition_via_api

DIRECTORY = pathlib.Path(__file__).parent.resolve()


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    @property
    def text(self):
        return """[
    {
        "element_id": "f49fbd614ddf5b72e06f59e554e6ae2b",
        "text": "This is a test email to use for unit tests.",
        "type": "NarrativeText",
        "metadata": {
            "date": "2022-12-16T17:04:16-05:00",
            "sent_from": [
                "Matthew Robinson <mrobinson@unstructured.io>"
            ],
            "sent_to": [
                "Matthew Robinson <mrobinson@unstructured.io>"
            ],
            "subject": "Test Email",
            "filename": "fake-email.eml"
        }
    }
]"""


def test_partition_via_api_from_filename(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(status_code=200),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")
    elements = partition_via_api(filename=filename, api_key="FAKEROO")
    assert elements[0] == NarrativeText("This is a test email to use for unit tests.")


def test_partition_via_api_from_file(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(status_code=200),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")

    with open(filename, "rb") as f:
        elements = partition_via_api(file=f, file_filename=filename, api_key="FAKEROO")
    assert elements[0] == NarrativeText("This is a test email to use for unit tests.")


def test_partition_via_api_raises_with_bad_response(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(status_code=500),
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email.eml")

    with pytest.raises(ValueError):
        partition_via_api(filename=filename, api_key="FAKEROO")
