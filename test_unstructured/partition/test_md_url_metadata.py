import pytest
import requests

from unstructured.partition.md import partition_md


@pytest.fixture
def markdown_response(mocker):
    response = requests.Response()
    response.status_code = 200
    response.encoding = "utf-8"
    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    response._content = b"# Heading\n\nThis paragraph describes the source document."
    fetch = mocker.patch("unstructured.partition.md.safe_get", return_value=response)
    html_fetch = mocker.patch("unstructured.partition.html.partition.safe_get")
    return response, fetch, html_fetch


@pytest.mark.parametrize("chunking_strategy", [None, "basic", "by_title"])
def test_markdown_url_is_preserved_in_element_metadata(markdown_response, chunking_strategy):
    _, fetch, html_fetch = markdown_response
    url = "https://example.test/source.md"

    elements = partition_md(url=url, languages=[""], chunking_strategy=chunking_strategy)

    assert elements
    assert all(element.metadata.url == url for element in elements)
    assert all(element.metadata.filetype == "text/markdown" for element in elements)
    fetch.assert_called_once_with(url)
    html_fetch.assert_not_called()


@pytest.mark.parametrize("content", [b"", b" \n \t"])
def test_empty_remote_markdown_does_not_trigger_an_html_fetch(markdown_response, content):
    response, fetch, html_fetch = markdown_response
    response._content = content

    assert partition_md(url="https://example.test/empty.md", languages=[""]) == []

    fetch.assert_called_once()
    html_fetch.assert_not_called()


def test_text_markdown_does_not_gain_url_metadata():
    elements = partition_md(text="# Heading", languages=[""], metadata_filename="source.md")

    assert elements
    assert all(element.metadata.url is None for element in elements)
    assert all(element.metadata.filename == "source.md" for element in elements)
