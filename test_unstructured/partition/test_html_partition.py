import os
import pathlib
import pytest

import re

from unittest.mock import patch


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
    with open(filename, "r") as f:
        elements = partition_html(file=f)
    assert len(elements) > 0


def test_partition_html_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename, "r") as f:
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
    with open(filename, "r") as f:
        text = f.read()

    response = MockResponse(text=text, status_code=200, headers={"Content-Type": "text/html"})
    with patch.object(requests, "get", return_value=response) as _:
        elements = partition_html(url="https://fake.url")

    assert len(elements) > 0


def test_partition_html_from_url_raises_with_bad_status_code():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename, "r") as f:
        text = f.read()

    response = MockResponse(text=text, status_code=500, headers={"Content-Type": "text/html"})
    with patch.object(requests, "get", return_value=response) as _:
        with pytest.raises(ValueError):
            partition_html(url="https://fake.url")


def test_partition_html_from_url_raises_with_bad_content_type():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename, "r") as f:
        text = f.read()

    response = MockResponse(
        text=text, status_code=200, headers={"Content-Type": "application/json"}
    )
    with patch.object(requests, "get", return_value=response) as _:
        with pytest.raises(ValueError):
            partition_html(url="https://fake.url")


def test_partition_html_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_html()


def test_partition_html_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename, "r") as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_html(filename=filename, text=text)


def test_partition_html_includes_javascript_function():
    regex_for_js_function = (
        r"function\s*([A-z0-9]+)?\s*\((?:[^)(]+|\((?:[^)(]+|\([^)(]*\))*\))*\)"
        r"\s*\{(?:[^}{]+|\{(?:[^}{]+|\{[^}{]*\})*\})*\}"
    )
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-script-html.html")
    with open(filename, "r") as f:
        file_text = f.read()
    elements = partition_html(text=file_text)
    text = "\n\n".join([str(el) for el in elements[:5]])
    content = re.search(regex_for_js_function, text, flags=0)
    check_js = True if content else False
    assert check_js is False
