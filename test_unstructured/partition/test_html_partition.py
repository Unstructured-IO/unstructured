import os
import pathlib
from unittest.mock import patch

import pytest
import requests
from requests.models import Response

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import EmailAddress, ListItem, NarrativeText, Table, Title
from unstructured.documents.html import HTMLTitle
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


def test_partition_html_from_filename_returns_html_elements():
    directory = os.path.join(DIRECTORY, "..", "..", "example-docs")
    filename = os.path.join(directory, "example-10k.html")
    elements = partition_html(filename=filename)
    assert len(elements) > 0
    assert isinstance(elements[0], HTMLTitle)


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
    [
        "example-10k-utf-16.html",
        "example-steelJIS-datasheet-utf-16.html",
        "fake-html-lang-de.html",
    ],
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
    [
        "example-10k-utf-16.html",
        "example-steelJIS-datasheet-utf-16.html",
        "fake-html-lang-de.html",
    ],
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
    [
        "example-10k-utf-16.html",
        "example-steelJIS-datasheet-utf-16.html",
        "fake-html-lang-de.html",
    ],
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

    response = MockResponse(
        text=text,
        status_code=200,
        headers={"Content-Type": "text/html"},
    )
    with patch.object(requests, "get", return_value=response) as _:
        elements = partition_html(url="https://fake.url")

    assert len(elements) > 0


def test_partition_html_from_url_raises_with_bad_status_code():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-10k.html")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(
        text=text,
        status_code=500,
        headers={"Content-Type": "text/html"},
    )
    with patch.object(requests, "get", return_value=response) as _, pytest.raises(ValueError):
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
    with patch.object(requests, "get", return_value=response) as _, pytest.raises(ValueError):
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


def test_partition_html_on_ideas_page(filename="example-docs/ideas-page.html"):
    elements = partition_html(filename=filename)
    assert len(elements) == 1
    assert elements[0] == Table(
        text="January 2023 ( Someone  fed my essays into GPT to make something "
        "that could answer\nquestions based on them, then asked it where good "
        "ideas come from.  The\nanswer was ok, but not what I would have said. "
        "This is what I would have said.) The way to get new ideas is to notice "
        "anomalies: what seems strange,\nor missing, or broken? You can see anomalies"
        " in everyday life (much\nof standup comedy is based on this), but the best "
        "place to look for\nthem is at the frontiers of knowledge. Knowledge grows "
        "fractally.\nFrom a distance its edges look smooth, but when you learn "
        "enough\nto get close to one, you'll notice it's full of gaps. These "
        "gaps\nwill seem obvious; it will seem inexplicable that no one has tried\nx "
        "or wondered about y. In the best case, exploring such gaps yields\nwhole "
        "new fractal buds.",
    )

    assert elements[0].metadata.emphasized_text_contents is None
    assert elements[0].metadata.link_urls is None
    assert elements[0].metadata.text_as_html is not None


def test_user_without_file_write_permission_can_partition_html(tmp_path, monkeypatch):
    example_filename = os.path.join(
        DIRECTORY,
        "..",
        "..",
        "example-docs",
        "example-10k.html",
    )

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
    assert clean_extra_whitespace(elements[0].text).startswith("[107th Congress Public Law 56]")
    assert isinstance(elements[0], NarrativeText)
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


def test_partition_html_metadata_date(mocker, filename="example-docs/fake-html.html"):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = partition_html(filename=filename)

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_html_from_file_metadata_date(
    mocker,
    filename="example-docs/fake-html.html",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename) as f:
        elements = partition_html(file=f)

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_html_custom_metadata_date(
    mocker,
    filename="example-docs/fake-html.html",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_html(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_html_from_file_custom_metadata_date(
    mocker,
    filename="example-docs/fake-html.html",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.html.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename) as f:
        elements = partition_html(
            file=f,
            metadata_last_modified=expected_last_modification_date,
        )

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_html_from_text_metadata_date(filename="example-docs/fake-html.html"):
    elements = partition_html(text="<html><div><p>TEST</p></div></html>")

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified is None


def test_partition_html_from_text_custom_metadata_date(
    filename="example-docs/fake-html.html",
):
    expected_last_modification_date = "2020-07-05T09:24:28"

    elements = partition_html(
        text="<html><div><p>TEST</p></div></html>",
        metadata_last_modified=expected_last_modification_date,
    )

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_html_grabs_links():
    html_text = """<html>
        <p>Hello there I am a <a href="/link">very important link!</a></p>
        <p>Here is a list of my favorite things</p>
        <ul>
            <li><a href="https://en.wikipedia.org/wiki/Parrot">Parrots</a></li>
            <li>Dogs</li>
        </ul>
        <a href="/loner">A lone link!</a>
    </html>"""
    elements = partition_html(text=html_text)

    assert elements[0] == NarrativeText("Hello there I am a very important link!")
    assert elements[0].metadata.link_urls == ["/link"]
    assert elements[0].metadata.link_texts == ["very important link!"]

    assert elements[1] == NarrativeText("Here is a list of my favorite things")
    assert elements[1].metadata.link_urls is None
    assert elements[1].metadata.link_texts is None

    assert elements[2] == ListItem("Parrots")
    assert elements[2].metadata.link_urls == ["https://en.wikipedia.org/wiki/Parrot"]
    assert elements[2].metadata.link_texts == ["Parrots"]

    assert elements[3] == ListItem("Dogs")
    assert elements[3].metadata.link_urls is None
    assert elements[3].metadata.link_texts is None

    assert elements[4] == Title("A lone link!")
    assert elements[4].metadata.link_urls == ["/loner"]
    assert elements[4].metadata.link_texts == ["A lone link!"]


def test_partition_html_from_filename_with_skip_headers_and_footers(
    filename="example-docs/fake-html-with-footer-and-header.html",
):
    elements = partition_html(filename=filename, skip_headers_and_footers=True)

    for element in elements:
        assert "footer" not in element.ancestortags
        assert "header" not in element.ancestortags


def test_partition_html_from_file_with_skip_headers_and_footers(
    filename="example-docs/fake-html-with-footer-and-header.html",
):
    with open(filename) as f:
        elements = partition_html(file=f, skip_headers_and_footers=True)

    for element in elements:
        assert "footer" not in element.ancestortags
        assert "header" not in element.ancestortags


def test_partition_html_from_text_with_skip_headers_and_footers():
    text = """
    <!DOCTYPE html>
    <html>
        <header>
            <p>Header</p>
        </header>
        <body>
            <h1>My First Heading</h1>
            <p>My first paragraph.</p>
        </body>
        <footer>
            <p>Footer</p>
        </footer>
    </html>"""
    elements = partition_html(text=text, skip_headers_and_footers=True)

    for element in elements:
        assert "footer" not in element.ancestortags
        assert "header" not in element.ancestortags


def test_partition_html_from_url_with_skip_headers_and_footers(mocker):
    test_url = "https://example.com"
    test_headers = {"User-Agent": "test"}

    response = Response()
    response.status_code = 200
    response._content = b"""<html>
        <header>
            <p>Header</p>
        </header>
        <body>
            <h1>My First Heading</h1>
            <p>My first paragraph.</p>
        </body>
        <footer>
            <p>Footer</p>
        </footer>
    </html>"""
    response.headers = {"Content-Type": "text/html"}

    mocker.patch("requests.get", return_value=response)

    elements = partition_html(url=test_url, headers=test_headers, skip_headers_and_footers=True)

    for element in elements:
        assert "footer" not in element.ancestortags
        assert "header" not in element.ancestortags


def test_partition_html_grabs_emphasized_texts():
    html_text = """<html>
        <p>Hello there I am a very <strong>important</strong> text!</p>
        <p>Here is a <span>list</span> of <b>my <i>favorite</i> things</b></p>
        <ul>
            <li><em>Parrots</em></li>
            <li>Dogs</li>
        </ul>
        <span>A lone span text!</span>
    </html>"""
    elements = partition_html(text=html_text)

    assert elements[0] == NarrativeText("Hello there I am a very important text!")
    assert elements[0].metadata.emphasized_text_contents == ["important"]
    assert elements[0].metadata.emphasized_text_tags == ["strong"]

    assert elements[1] == NarrativeText("Here is a list of my favorite things")
    assert elements[1].metadata.emphasized_text_contents == [
        "list",
        "my favorite things",
        "favorite",
    ]
    assert elements[1].metadata.emphasized_text_tags == ["span", "b", "i"]

    assert elements[2] == ListItem("Parrots")
    assert elements[2].metadata.emphasized_text_contents == ["Parrots"]
    assert elements[2].metadata.emphasized_text_tags == ["em"]

    assert elements[3] == ListItem("Dogs")
    assert elements[3].metadata.emphasized_text_contents is None
    assert elements[3].metadata.emphasized_text_tags is None

    assert elements[4] == Title("A lone span text!")
    assert elements[4].metadata.emphasized_text_contents == ["A lone span text!"]
    assert elements[4].metadata.emphasized_text_tags == ["span"]


def test_partition_html_with_json():
    elements = partition_html(example_doc_path("example-10k.html"))
    assert_round_trips_through_JSON(elements)


def test_pre_tag_parsing_respects_order():
    html_text = """
    <pre>The Big Brown Bear</pre>
    <div>The big brown bear is growling.</div>
    <pre>The big brown bear is sleeping.</pre>
    <div>The Big Blue Bear</div>
    """
    elements = partition_html(text=html_text)
    assert elements == [
        Title("The Big Brown Bear"),
        NarrativeText("The big brown bear is growling."),
        NarrativeText("The big brown bear is sleeping."),
        Title("The Big Blue Bear"),
    ]


def test_add_chunking_strategy_on_partition_html(
    filename="example-docs/example-10k.html",
):
    elements = partition_html(filename=filename)
    chunk_elements = partition_html(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_html_heading_title_detection():
    html_text = """
    <p>This is a section of narrative text, it's long, flows and has meaning</p>
    <h1>This is a section of narrative text, it's long, flows and has meaning</h1>
    <h2>A heading that is at the second level</h2>
    <h3>Finally, the third heading</h3>
    <h2>December 1-17, 2017</h2>
    <h3>email@example.com</h3>
    <h3><li>- bulleted item</li></h3>
    """
    elements = partition_html(text=html_text)
    assert elements == [
        NarrativeText("This is a section of narrative text, it's long, flows and has meaning"),
        Title("This is a section of narrative text, it's long, flows and has meaning"),
        Title("A heading that is at the second level"),
        Title("Finally, the third heading"),
        Title("December 1-17, 2017"),
        EmailAddress("email@example.com"),
        ListItem("- bulleted item"),
    ]


def test_partition_html_element_metadata_has_languages():
    filename = "example-docs/example-10k.html"
    elements = partition_html(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_html_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.html"
    elements = partition_html(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("thead", "<table><tr><td>Header 1</td><td>Header 2</td></tr></table>"),
        ("tfoot", "<table><tr><td>Header 1</td><td>Header 2</td></tr></table>"),
    ],
)
def test_partition_html_with_table_without_tbody(tag: str, expected: str):
    table_html = (
        f"<table>\n"
        f"  <{tag}>\n"
        f"    <tr><th>Header 1</th><th>Header 2</th></tr>\n"
        f"  </{tag}>\n"
        f"</table>"
    )
    partitions = partition_html(text=table_html)
    assert partitions[0].metadata.text_as_html == expected
