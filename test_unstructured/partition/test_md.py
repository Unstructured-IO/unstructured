import os
import pathlib
from unittest.mock import patch

import pytest
import requests

from unstructured.documents.elements import PageBreak
from unstructured.partition.md import partition_md

DIRECTORY = pathlib.Path(__file__).parent.resolve()


def test_partition_md_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "README.md")
    elements = partition_md(filename=filename)
    assert PageBreak() not in elements
    assert len(elements) > 0


def test_partition_md_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        elements = partition_md(file=f)
    assert len(elements) > 0


def test_partition_md_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()
    elements = partition_md(text=text)
    assert len(elements) > 0


class MockResponse:
    def __init__(self, text, status_code, headers={}):
        self.text = text
        self.status_code = status_code
        self.ok = status_code < 300
        self.headers = headers


def test_partition_md_from_url():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(text=text, status_code=200, headers={"Content-Type": "text/markdown"})
    with patch.object(requests, "get", return_value=response) as _:
        elements = partition_md(url="https://fake.url")

    assert len(elements) > 0


def test_partition_md_from_url_raises_with_bad_status_code():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(text=text, status_code=500, headers={"Content-Type": "text/html"})
    with patch.object(requests, "get", return_value=response) as _:
        with pytest.raises(ValueError):
            partition_md(url="https://fake.url")


def test_partition_md_from_url_raises_with_bad_content_type():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(
        text=text,
        status_code=200,
        headers={"Content-Type": "application/json"},
    )
    with patch.object(requests, "get", return_value=response) as _:
        with pytest.raises(ValueError):
            partition_md(url="https://fake.url")


def test_partition_md_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_md()


def test_partition_md_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "README.md")
    with open(filename) as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_md(filename=filename, text=text)
