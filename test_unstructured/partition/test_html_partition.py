import os
import pathlib
from unittest.mock import patch

import pytest
import requests

from unstructured.documents.elements import PageBreak
from unstructured.partition.html import partition_html

DIRECTORY = pathlib.Path(__file__).parent.resolve()


def test_partition_html_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    elements = partition_html(filename=filename)
    assert PageBreak() not in elements
    assert len(elements) > 0


def test_partition_html_with_page_breaks():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    elements = partition_html(filename=filename, include_page_breaks=True)
    assert PageBreak() in elements
    assert len(elements) > 0


def test_partition_html_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        elements = partition_html(file=f)
    assert len(elements) > 0


def test_partition_html_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        text = f.read()
    elements = partition_html(text=text)
    assert len(elements) > 0


class MockResponse:
    def __init__(self, text, status_code, headers={}):
        self.text = text
        self.status_code = status_code
        self.ok = status_code < 300
        self.headers = headers


def test_partition_html_from_url():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(text=text, status_code=200, headers={"Content-Type": "text/html"})
    with patch.object(requests, "get", return_value=response) as _:
        elements = partition_html(url="https://fake.url")

    assert len(elements) > 0


def test_partition_html_from_url_raises_with_bad_status_code():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(text=text, status_code=500, headers={"Content-Type": "text/html"})
    with patch.object(requests, "get", return_value=response) as _:
        with pytest.raises(ValueError):
            partition_html(url="https://fake.url")


def test_partition_html_from_url_raises_with_bad_content_type():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(
        text=text,
        status_code=200,
        headers={"Content-Type": "application/json"},
    )
    with patch.object(requests, "get", return_value=response) as _:
        with pytest.raises(ValueError):
            partition_html(url="https://fake.url")


def test_partition_html_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_html()


def test_partition_html_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_html(filename=filename, text=text)


def test_partition_html_on_ideas_page():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "ideas-page.html")
    elements = partition_html(filename=filename)
    document_text = "\n\n".join([str(el) for el in elements])
    assert document_text.startswith("January 2023(Someone fed my essays into GPT")
    assert document_text.endswith("whole new fractal buds.")


def test_user_without_file_write_permission_can_partition_html(tmp_path, monkeypatch):
    example_filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")

    ***REMOVED*** create a file with no write permissions
    read_only_file = tmp_path / "example-10k-readonly.html"
    read_only_file.touch()

    ***REMOVED*** set content of read_only_file to be that of example-10k.html
    with open(example_filename) as f:
        read_only_file.write_text(f.read())

    ***REMOVED*** set read_only_file to be read only
    read_only_file.chmod(0o444)

    ***REMOVED*** partition html should still work
    elements = partition_html(filename=read_only_file.resolve())
    assert len(elements) > 0
