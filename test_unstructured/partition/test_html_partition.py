import os
import pathlib
from unittest.mock import patch

import pytest
import requests
from requests.models import Response

from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Title
from unstructured.partition.html import partition_html

DIRECTORY = pathlib.Path(__file__).parent.resolve()

EXPECTED_OUTPUT_LANGUAGE_DE = [
    Title(text="Jahresabschluss zum Geschäftsjahr vom 01.01.2020 bis zum 31.12.2020"),
]


def test_partition_html_from_filename():
    directory = os.path.join(DIRECTORY, "..", "..", "example-docs")
    filename = os.path.join(directory, "example-10k.html")
    elements = partition_html(filename=filename)
    assert len(elements) > 0
    assert "PageBreak" not in [elem.category for elem in elements]
    assert elements[0].metadata.filename == "example-10k.html"
    assert elements[0].metadata.file_directory == directory


def test_partition_html_from_filename_with_metadata_filename():
    directory = os.path.join(DIRECTORY, "..", "..", "example-docs")
    filename = os.path.join(directory, "example-10k.html")
    elements = partition_html(filename=filename, metadata_filename="test")
    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


@pytest.mark.parametrize(
    ("filename", "encoding", "error"),
    [
        ("example-10k-utf-16.html", "utf-8", UnicodeDecodeError),
        ("example-steelJIS-datasheet-utf-16.html", "utf-8", UnicodeDecodeError),
    ],
)
def test_partition_html_from_filename_raises_encoding_error(filename, encoding, error):
    with pytest.raises(error):
        filename = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
        with open(filename) as f:
            partition_html(file=f, encoding=encoding)


@pytest.mark.parametrize(
    "filename",
    ["example-10k-utf-16.html", "example-steelJIS-datasheet-utf-16.html", "fake-html-lang-de.html"],
)
def test_partition_html_from_filename_default_encoding(filename):
    filename_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition_html(filename=filename_path)
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename == filename
    if filename == "fake-html-lang-de.html":
        assert elements == EXPECTED_OUTPUT_LANGUAGE_DE


def test_partition_html_from_filename_metadata_false():
    directory = os.path.join(DIRECTORY, "..", "..", "example-docs")
    filename = os.path.join(directory, "example-10k.html")
    elements = partition_html(filename=filename, include_metadata=False)
    metadata_present = any(element.metadata.to_dict() for element in elements)
    assert not metadata_present


def test_partition_html_with_page_breaks():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    elements = partition_html(filename=filename, include_page_breaks=True)
    assert "PageBreak" in [elem.category for elem in elements]
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename == "example-10k.html"


def test_partition_html_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        elements = partition_html(file=f)
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename is None


def test_partition_html_from_file_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        elements = partition_html(file=f, metadata_filename="test")
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename == "test"


@pytest.mark.parametrize(
    ("filename", "encoding", "error"),
    [
        ("example-10k-utf-16.html", "utf-8", UnicodeDecodeError),
        ("example-steelJIS-datasheet-utf-16.html", "utf-8", UnicodeDecodeError),
    ],
)
def test_partition_html_from_file_raises_encoding_error(filename, encoding, error):
    with pytest.raises(error):
        filename = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
        with open(filename) as f, pytest.raises(UnicodeEncodeError):
            partition_html(file=f, encoding=encoding)


@pytest.mark.parametrize(
    "filename",
    ["example-10k-utf-16.html", "example-steelJIS-datasheet-utf-16.html", "fake-html-lang-de.html"],
)
def test_partition_html_from_file_default_encoding(filename):
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(filename) as f:
        elements = partition_html(file=f)
    assert len(elements) > 0
    if filename == "fake-html-lang-de.html":
        assert elements == EXPECTED_OUTPUT_LANGUAGE_DE


@pytest.mark.parametrize(
    ("filename", "encoding", "error"),
    [
        ("example-10k-utf-16.html", "utf-8", UnicodeDecodeError),
        ("example-steelJIS-datasheet-utf-16.html", "utf-8", UnicodeDecodeError),
    ],
)
def test_partition_html_from_file_rb_raises_encoding_error(filename, encoding, error):
    with pytest.raises(error):
        filename = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
        with open(filename, "rb") as f:
            partition_html(file=f, encoding=encoding)


@pytest.mark.parametrize(
    "filename",
    ["example-10k-utf-16.html", "example-steelJIS-datasheet-utf-16.html", "fake-html-lang-de.html"],
)
def test_partition_html_from_file_rb_default_encoding(filename):
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(filename, "rb") as f:
        elements = partition_html(file=f)
    assert len(elements) > 0
    if filename == "fake-html-lang-de.html":
        assert elements == EXPECTED_OUTPUT_LANGUAGE_DE


def test_partition_html_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        text = f.read()
    elements = partition_html(text=text)
    assert len(elements) > 0


def test_partition_html_from_text_works_with_empty_string():
    assert partition_html(text="") == []


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


def test_partition_from_url_uses_headers(mocker):
    test_url = "https://example.com"
    test_headers = {"User-Agent": "test"}

    response = Response()
    response.status_code = 200
    response._content = (
        b"<html><head></head><body><p>What do i know? Who needs to know it?</p></body></html>"
    )
    response.headers = {"Content-Type": "text/html"}

    mock_get = mocker.patch("requests.get", return_value=response)

    partition_html(url=test_url, headers=test_headers)

    # Check if requests.get was called with the correct arguments
    mock_get.assert_called_once_with(test_url, headers=test_headers, verify=True)


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

    # create a file with no write permissions
    read_only_file = tmp_path / "example-10k-readonly.html"
    read_only_file.touch()

    # set content of read_only_file to be that of example-10k.html
    with open(example_filename) as f:
        read_only_file.write_text(f.read())

    # set read_only_file to be read only
    read_only_file.chmod(0o444)

    # partition html should still work
    elements = partition_html(filename=read_only_file.resolve())
    assert len(elements) > 0


def test_partition_html_processes_chinese_chracters():
    html_text = "<html><div><p>每日新闻</p></div></html>"
    elements = partition_html(text=html_text)
    assert elements[0].text == "每日新闻"


def test_emoji_appears_with_emoji_utf8_code():
    html_text = """\n<html charset="utf-8"><p>Hello &#128512;</p></html>"""
    elements = partition_html(text=html_text)
    assert elements[0] == Title("Hello 😀")


def test_partition_html_can_turn_off_assemble_articles():
    html_text = """<html>
    <article>
        <h1>Some important stuff is going on!</h1>
        <p>Here is a description of that stuff</p>
    </article>
    <article>
        <h1>Some other important stuff is going on!</h1>
        <p>Here is a description of that stuff</p>
    </article>
    <h4>This is outside of the article.</h4>
</html>
"""
    elements = partition_html(text=html_text, html_assemble_articles=False)
    assert elements[-1] == Title("This is outside of the article.")


def test_partition_html_with_pre_tag():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-html-pre.htm")
    elements = partition_html(filename=filename)

    assert len(elements) > 0
    assert "PageBreak" not in [elem.category for elem in elements]
    assert clean_extra_whitespace(elements[0].text) == "[107th Congress Public Law 56]"
    assert isinstance(elements[0], Title)
    assert elements[0].metadata.filetype == "text/html"
    assert elements[0].metadata.filename == "fake-html-pre.htm"


def test_partition_html_from_filename_exclude_metadata():
    directory = os.path.join(DIRECTORY, "..", "..", "example-docs")
    filename = os.path.join(directory, "example-10k.html")
    elements = partition_html(filename=filename, include_metadata=False)
    assert len(elements) > 0
    assert "PageBreak" not in [elem.category for elem in elements]
    assert elements[0].metadata.filename is None
    assert elements[0].metadata.file_directory is None
