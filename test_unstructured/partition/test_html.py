"""Test suite for `unstructured.partition.html` module."""

from __future__ import annotations

import io
import pathlib
from tempfile import SpooledTemporaryFile
from typing import cast

import pytest

from test_unstructured.unit_utils import (
    Mock,
    MonkeyPatch,
    assert_round_trips_through_JSON,
    example_doc_path,
    example_doc_text,
    function_mock,
)
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import (
    CompositeElement,
    EmailAddress,
    ListItem,
    NarrativeText,
    Table,
    TableChunk,
    Title,
)
from unstructured.documents.html_elements import HTMLTable, TagsMixin
from unstructured.partition.html import partition_html

# -- document-source (filename, file, text, url) -------------------------------------------------


def test_partition_html_accepts_a_file_path():
    elements = partition_html(example_doc_path("example-10k-1p.html"))

    assert len(elements) > 0
    assert all(e.metadata.filename == "example-10k-1p.html" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("") for e in elements)


def test_partition_html_accepts_a_file_like_object():
    with open(example_doc_path("example-10k-1p.html"), "rb") as f:
        elements = partition_html(file=f)

    assert len(elements) > 0
    assert all(e.metadata.filename is None for e in elements)


def test_partition_html_accepts_an_html_str():
    elements = partition_html(text=example_doc_text("example-10k-1p.html"))
    assert len(elements) > 0


def test_partition_html_accepts_a_url_to_an_HTML_document(requests_get_: Mock):
    requests_get_.return_value = FakeResponse(
        text=example_doc_text("example-10k-1p.html"),
        status_code=200,
        headers={"Content-Type": "text/html"},
    )

    elements = partition_html(url="https://fake.url")

    requests_get_.assert_called_once_with("https://fake.url", headers={}, verify=True)
    assert len(elements) > 0


def test_partition_html_raises_when_no_path_or_file_or_text_or_url_is_specified():
    with pytest.raises(ValueError):
        partition_html()


def test_partition_html_raises_with_too_many_specified():
    with pytest.raises(ValueError):
        partition_html(
            example_doc_path("example-10k-1p.html"), text=example_doc_text("example-10k-1p.html")
        )


# -- partition_html() from URL -------------------------------------------------------------------


def test_partition_html_from_url_raises_on_failure_response_status_code(requests_get_: Mock):
    requests_get_.return_value = FakeResponse(
        text=example_doc_text("example-10k-1p.html"),
        status_code=500,
        headers={"Content-Type": "text/html"},
    )

    with pytest.raises(ValueError, match="Error status code on GET of provided URL: 500"):
        partition_html(url="https://fake.url")


def test_partition_html_from_url_raises_on_response_of_wrong_content_type(requests_get_: Mock):
    requests_get_.return_value = FakeResponse(
        text=example_doc_text("example-10k-1p.html"),
        status_code=200,
        headers={"Content-Type": "application/json"},
    )

    with pytest.raises(ValueError, match="Expected content type text/html. Got application/json."):
        partition_html(url="https://fake.url")


def test_partition_from_url_includes_provided_headers_in_request(requests_get_: Mock):
    requests_get_.return_value = FakeResponse(
        text="<html><head></head><body><p>What do I know? Who needs to know it?</p></body></html>",
        status_code=200,
        headers={"Content-Type": "text/html"},
    )

    partition_html(url="https://example.com", headers={"User-Agent": "test"})

    requests_get_.assert_called_once_with(
        "https://example.com", headers={"User-Agent": "test"}, verify=True
    )


# -- HTML tag-specific behaviors -----------------------------------------------------------------


def test_partition_html_recognizes_h1_to_h3_as_Title_except_in_edge_cases():
    assert partition_html(
        text=(
            "<p>This is a section of narrative text, it's long, flows and has meaning</p>\n"
            "<h1>This heading is a title, even though it's long, flows and has meaning</h1>\n"
            "<h2>A heading that is at the second level</h2>\n"
            "<h3>Finally, the third heading</h3>\n"
            "<h2>December 1-17, 2017</h2>\n"
            "<h3>email@example.com</h3>\n"
            "<h3><li>- bulleted item</li></h3>\n"
        )
    ) == [
        NarrativeText("This is a section of narrative text, it's long, flows and has meaning"),
        Title("This heading is a title, even though it's long, flows and has meaning"),
        Title("A heading that is at the second level"),
        Title("Finally, the third heading"),
        Title("December 1-17, 2017"),
        EmailAddress("email@example.com"),
        ListItem("- bulleted item"),
    ]


def test_partition_html_with_pre_tag():
    elements = partition_html(example_doc_path("fake-html-pre.htm"))

    assert len(elements) > 0
    assert all(e.category != "PageBreak" for e in elements)
    assert clean_extra_whitespace(elements[0].text).startswith("[107th Congress Public Law 56]")
    assert isinstance(elements[0], NarrativeText)
    assert elements[0].metadata.filetype == "text/html"
    assert elements[0].metadata.filename == "fake-html-pre.htm"


def test_pre_tag_parsing_respects_order():
    assert partition_html(
        text=(
            "<pre>The Big Brown Bear</pre>\n"
            "<div>The big brown bear is growling.</div>\n"
            "<pre>The big brown bear is sleeping.</pre>\n"
            "<div>The Big Blue Bear</div>\n"
        )
    ) == [
        Title("The Big Brown Bear"),
        NarrativeText("The big brown bear is growling."),
        NarrativeText("The big brown bear is sleeping."),
        Title("The Big Blue Bear"),
    ]


@pytest.mark.parametrize(
    ("tag", "expected_text_as_html"),
    [
        ("thead", "<table><tr><td>Header 1</td><td>Header 2</td></tr></table>"),
        ("tfoot", "<table><tr><td>Header 1</td><td>Header 2</td></tr></table>"),
    ],
)
def test_partition_html_with_table_without_tbody(tag: str, expected_text_as_html: str):
    elements = partition_html(
        text=(
            f"<table>\n"
            f"  <{tag}>\n"
            f"    <tr><th>Header 1</th><th>Header 2</th></tr>\n"
            f"  </{tag}>\n"
            f"</table>"
        )
    )
    assert elements[0].metadata.text_as_html == expected_text_as_html


def test_partition_html_b_tag_parsing():
    elements = partition_html(
        text=(
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<body>\n"
            "<div>\n"
            "  <h1>Header 1</h1>\n"
            "  <p>Text</p>\n"
            "  <h2>Header 2</h2>\n"
            "  <pre>\n"
            "    <b>Param1</b> = Y<br><b>Param2</b> = 1<br><b>Param3</b> = 2<br><b>Param4</b> = A\n"
            "    <br><b>Param5</b> = A,B,C,D,E<br><b>Param6</b> = 7<br><b>Param7</b> = Five<br>\n"
            "  </pre>\n"
            "</div>\n"
            "</body>\n"
            "</html>\n"
        )
    )
    assert "|".join(e.text for e in elements) == (
        "Header 1|Text|Header 2|Param1 = Y|Param2 = 1|Param3 = 2|Param4 = A|"
        "Param5 = A,B,C,D,E|Param6 = 7|Param7 = Five"
    )


def test_partition_html_tag_tail_parsing():
    elements = partition_html(
        text=(
            "<html>\n"
            "<body>\n"
            "<div>\n"
            "    Head\n"
            "    <div><span>Nested</span></div>\n"
            "    Tail\n"
            "</div>\n"
            "</body>\n"
            "</html>\n"
        )
    )
    assert "|".join([str(e).strip() for e in elements]) == "Head|Nested|Tail"


# -- `chunking_strategy` arg ---------------------------------------------------------------------


def test_partition_html_can_chunk_while_partitioning():
    file_path = example_doc_path("example-10k-1p.html")
    chunks = partition_html(file_path, chunking_strategy="by_title")
    chunks_2 = chunk_by_title(partition_html(file_path))
    assert all(isinstance(c, (CompositeElement, Table, TableChunk)) for c in chunks)
    assert chunks == chunks_2


# -- `encoding` arg ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename", ["example-10k-utf-16.html", "example-steelJIS-datasheet-utf-16.html"]
)
def test_partition_html_from_filename_raises_when_explicit_encoding_is_wrong(filename: str):
    with pytest.raises(UnicodeDecodeError):
        with open(example_doc_path(filename), "rb") as f:
            partition_html(file=f, encoding="utf-8")


@pytest.mark.parametrize(
    "filename",
    ["example-10k-utf-16.html", "example-steelJIS-datasheet-utf-16.html", "fake-html-lang-de.html"],
)
def test_partition_html_from_filename_default_encoding(filename: str):
    elements = partition_html(example_doc_path(filename))

    assert len(elements) > 0
    assert all(e.metadata.filename == filename for e in elements)
    if filename == "fake-html-lang-de.html":
        assert elements == EXPECTED_OUTPUT_LANGUAGE_DE


@pytest.mark.parametrize(
    "filename", ["example-10k-utf-16.html", "example-steelJIS-datasheet-utf-16.html"]
)
def test_partition_html_from_file_raises_encoding_error(filename: str):
    with open(example_doc_path(filename), "rb") as f:
        file = io.BytesIO(f.read())

    with pytest.raises(UnicodeDecodeError, match="'utf-8' codec can't decode byte 0xff in posi"):
        partition_html(file=file, encoding="utf-8")


@pytest.mark.parametrize(
    "filename",
    ["example-10k-utf-16.html", "example-steelJIS-datasheet-utf-16.html", "fake-html-lang-de.html"],
)
def test_partition_html_from_file_default_encoding(filename: str):
    with open(example_doc_path(filename), "rb") as f:
        elements = partition_html(file=f)

    assert len(elements) > 0
    if filename == "fake-html-lang-de.html":
        assert elements == EXPECTED_OUTPUT_LANGUAGE_DE


@pytest.mark.parametrize(
    "filename", ["example-10k-utf-16.html", "example-steelJIS-datasheet-utf-16.html"]
)
def test_partition_html_from_file_rb_raises_encoding_error(filename: str):
    with pytest.raises(UnicodeDecodeError, match="'utf-8' codec can't decode byte 0xff in posi"):
        with open(example_doc_path(filename), "rb") as f:
            partition_html(file=f, encoding="utf-8")


@pytest.mark.parametrize(
    "filename",
    ["example-10k-utf-16.html", "example-steelJIS-datasheet-utf-16.html", "fake-html-lang-de.html"],
)
def test_partition_html_from_file_rb_default_encoding(filename: str):
    with open(example_doc_path(filename), "rb") as f:
        elements = partition_html(file=f)

    assert len(elements) > 0
    if filename == "fake-html-lang-de.html":
        assert elements == EXPECTED_OUTPUT_LANGUAGE_DE


def test_partition_html_processes_chinese_chracters():
    html_text = "<html><div><p>每日新闻</p></div></html>"
    elements = partition_html(text=html_text)
    assert elements[0].text == "每日新闻"


def test_emoji_appears_with_emoji_utf8_code():
    html_text = '<html charset="utf-8"><p>Hello &#128512;</p></html>'
    elements = partition_html(text=html_text)
    assert elements[0] == Title("Hello 😀")


# -- `include_metadata` arg ----------------------------------------------------------------------


def test_partition_html_from_filename_can_suppress_metadata():
    elements = partition_html(example_doc_path("example-10k-1p.html"), include_metadata=False)
    assert all(e.metadata.to_dict() == {} for e in elements)


# -- `include_page_breaks` arg -------------------------------------------------------------------


def test_partition_html_generates_no_page_breaks_by_default():
    elements = partition_html(example_doc_path("example-10k-1p.html"))
    assert all(e.category != "PageBreak" for e in elements)


def test_partition_html_generates_page_breaks_when_so_instructed():
    elements = partition_html(example_doc_path("example-10k-1p.html"), include_page_breaks=True)

    assert any(e.category == "PageBreak" for e in elements)
    assert all(e.metadata.filename == "example-10k-1p.html" for e in elements)


def test_partition_html_can_turn_off_assemble_articles():
    html_text = (
        "<html>\n"
        "   <article>\n"
        "       <h1>Some important stuff is going on!</h1>\n"
        "       <p>Here is a description of that stuff</p>\n"
        "   </article>\n"
        "   <article>\n"
        "       <h1>Some other important stuff is going on!</h1>\n"
        "       <p>Here is a description of that stuff</p>\n"
        "   </article>\n"
        "   <h4>This is outside of the article.</h4>\n"
        "</html>\n"
    )
    elements = partition_html(text=html_text, html_assemble_articles=False)
    assert elements[-1] == Title("This is outside of the article.")


# -- `skip_headers_and_footers` arg --------------------------------------------------------------


def test_partition_html_from_filename_can_skip_headers_and_footers():
    elements = cast(
        list[TagsMixin],
        partition_html(
            filename=example_doc_path("fake-html-with-footer-and-header.html"),
            skip_headers_and_footers=True,
        ),
    )

    assert all("header" not in e.ancestortags for e in elements)
    assert all("footer" not in e.ancestortags for e in elements)


def test_partition_html_from_file_can_skip_headers_and_footers():
    with open(example_doc_path("fake-html-with-footer-and-header.html"), "rb") as f:
        elements = cast(list[TagsMixin], partition_html(file=f, skip_headers_and_footers=True))

    assert all("header" not in e.ancestortags for e in elements)
    assert all("footer" not in e.ancestortags for e in elements)


def test_partition_html_from_text_can_skip_headers_and_footers():
    elements = cast(
        list[TagsMixin],
        partition_html(
            text=(
                "<!DOCTYPE html>\n"
                "<html>\n"
                "    <header>\n"
                "        <p>Header</p>\n"
                "    </header>\n"
                "    <body>\n"
                "        <h1>My First Heading</h1>\n"
                "        <p>My first paragraph.</p>\n"
                "    </body>\n"
                "    <footer>\n"
                "        <p>Footer</p>\n"
                "    </footer>\n"
                "</html>\n"
            ),
            skip_headers_and_footers=True,
        ),
    )

    assert all("header" not in e.ancestortags for e in elements)
    assert all("footer" not in e.ancestortags for e in elements)


def test_partition_html_from_url_can_skip_headers_and_footers(requests_get_: Mock):
    requests_get_.return_value = FakeResponse(
        text=(
            "<html>\n"
            "  <header>\n"
            "    <p>Header</p>\n"
            "  </header>\n"
            "  <body>\n"
            "    <h1>My First Heading</h1>\n"
            "    <p>My first paragraph.</p>\n"
            "  </body>\n"
            "  <footer>\n"
            "    <p>Footer</p>\n"
            "  </footer>\n"
            "</html>\n"
        ),
        status_code=200,
        headers={"Content-Type": "text/html"},
    )

    elements = cast(
        list[TagsMixin],
        partition_html(
            url="https://example.com", headers={"User-Agent": "test"}, skip_headers_and_footers=True
        ),
    )

    requests_get_.assert_called_once_with(
        "https://example.com", headers={"User-Agent": "test"}, verify=True
    )
    assert all("header" not in e.ancestortags for e in elements)
    assert all("footer" not in e.ancestortags for e in elements)


# -- `unique_element_ids` arg --------------------------------------------------------------------


def test_all_element_ids_are_unique():
    ids = [e.id for e in partition_html(example_doc_path("fake-html-with-duplicate-elements.html"))]
    assert len(ids) == len(set(ids))


def test_element_ids_are_deterministic():
    ids = [e.id for e in partition_html("example-docs/fake-html-with-duplicate-elements.html")]
    ids_2 = [e.id for e in partition_html("example-docs/fake-html-with-duplicate-elements.html")]
    assert ids == ids_2


# -- .metadata.emphasis --------------------------------------------------------------------------


def test_partition_html_grabs_emphasized_texts():
    elements = partition_html(
        text=(
            "<html>\n"
            "  <p>Hello there I am a very <strong>important</strong> text!</p>\n"
            "  <p>Here is a <span>list</span> of <b>my <i>favorite</i> things</b></p>\n"
            "  <ul>\n"
            "    <li><em>Parrots</em></li>\n"
            "    <li>Dogs</li>\n"
            "  </ul>\n"
            "  <span>A lone span text!</span>\n"
            "</html>\n"
        )
    )
    e = elements[0]
    assert e == NarrativeText("Hello there I am a very important text!")
    assert e.metadata.emphasized_text_contents == ["important"]
    assert e.metadata.emphasized_text_tags == ["strong"]
    e = elements[1]
    assert e == NarrativeText("Here is a list of my favorite things")
    assert e.metadata.emphasized_text_contents == ["list", "my favorite things", "favorite"]
    assert e.metadata.emphasized_text_tags == ["span", "b", "i"]
    e = elements[2]
    assert e == ListItem("Parrots")
    assert e.metadata.emphasized_text_contents == ["Parrots"]
    assert e.metadata.emphasized_text_tags == ["em"]
    e = elements[3]
    assert e == ListItem("Dogs")
    assert e.metadata.emphasized_text_contents is None
    assert e.metadata.emphasized_text_tags is None
    e = elements[4]
    assert e == Title("A lone span text!")
    assert e.metadata.emphasized_text_contents == ["A lone span text!"]
    assert e.metadata.emphasized_text_tags == ["span"]


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_html_from_filename_prefers_metadata_filename():
    elements = partition_html(example_doc_path("example-10k-1p.html"), metadata_filename="test")

    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_html_from_file_prefers_metadata_filename():
    with open(example_doc_path("example-10k-1p.html"), "rb") as f:
        elements = partition_html(file=f, metadata_filename="test")

    assert len(elements) > 0
    assert all(e.metadata.filename == "test" for e in elements)


# -- .metadata.languages -------------------------------------------------------------------------


def test_partition_html_element_metadata_has_languages():
    elements = partition_html(example_doc_path("example-10k-1p.html"))
    assert elements[0].metadata.languages == ["eng"]


def test_partition_html_respects_detect_language_per_element():
    elements = partition_html(
        example_doc_path("language-docs/eng_spa_mult.html"), detect_language_per_element=True
    )

    assert [e.metadata.languages for e in elements] == [
        ["eng"],
        ["spa", "eng"],
        ["eng"],
        ["eng"],
        ["spa"],
    ]


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_html_from_filename_pulls_last_modified_from_filesystem(
    get_last_modified_date_: Mock,
):
    last_modified_on_filesystem = "2023-07-05T09:24:28"
    get_last_modified_date_.return_value = last_modified_on_filesystem

    elements = partition_html(example_doc_path("fake-html.html"))

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified == last_modified_on_filesystem


def test_partition_html_from_filename_prefers_metadata_last_modified(
    get_last_modified_date_: Mock,
):
    metadata_last_modified = "2023-07-05T09:24:28"
    get_last_modified_date_.return_value = "2024-06-04T09:24:28"

    elements = partition_html(
        example_doc_path("fake-html.html"), metadata_last_modified=metadata_last_modified
    )

    assert isinstance(elements[0], Title)
    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_html_from_file_does_not_assign_last_modified_metadata_by_default(
    get_last_modified_date_from_file_: Mock,
):
    get_last_modified_date_from_file_.return_value = "2029-07-05T09:24:28"

    with open(example_doc_path("fake-html.html"), "rb") as f:
        elements = partition_html(file=f)

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified is None


def test_partition_html_from_file_pulls_last_modified_from_file_like_object_when_so_instructed(
    get_last_modified_date_from_file_: Mock,
):
    get_last_modified_date_from_file_.return_value = "2024-06-04T09:24:28"

    with open(example_doc_path("fake-html.html"), "rb") as f:
        elements = partition_html(file=f, date_from_file_object=True)

    assert isinstance(elements[0], Title)
    assert all(e.metadata.last_modified == "2024-06-04T09:24:28" for e in elements)


def test_partition_html_from_file_assigns_no_last_modified_metadata_when_file_has_none():
    """Test partition_html() with file that are not possible to get last modified date"""
    with open(example_doc_path("fake-html.html"), "rb") as f:
        sf = SpooledTemporaryFile()
        sf.write(f.read())
        sf.seek(0)
        elements = partition_html(file=sf, date_from_file_object=True)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_html_from_file_prefers_metadata_last_modified(
    get_last_modified_date_from_file_: Mock,
):
    metadata_last_modified = "2023-07-05T09:24:28"
    get_last_modified_date_from_file_.return_value = "2024-06-04T09:24:28"

    with open(example_doc_path("fake-html.html"), "rb") as f:
        elements = partition_html(file=f, metadata_last_modified=metadata_last_modified)

    assert isinstance(elements[0], Title)
    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_html_from_text_assigns_no_last_modified_metadata():
    elements = partition_html(text="<html><div><p>TEST</p></div></html>")

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified is None


def test_partition_html_from_text_prefers_metadata_last_modified():
    metadata_last_modified = "2023-07-05T09:24:28"

    elements = partition_html(
        text="<html><div><p>TEST</p></div></html>", metadata_last_modified=metadata_last_modified
    )

    assert isinstance(elements[0], Title)
    assert elements[0].metadata.last_modified == metadata_last_modified


# -- .metadata.link* -----------------------------------------------------------------------------


def test_partition_html_grabs_links():
    elements = partition_html(
        text=(
            "<html>\n"
            '  <p>Hello there I am a <a href="/link">very important link!</a></p>\n'
            "  <p>Here is a list of my favorite things</p>\n"
            "  <ul>\n"
            '    <li><a href="https://en.wikipedia.org/wiki/Parrot">Parrots</a></li>\n'
            "    <li>Dogs</li>\n"
            "  </ul>\n"
            '  <a href="/loner">A lone link!</a>\n'
            "</html>\n"
        )
    )

    e = elements[0]
    assert e == NarrativeText("Hello there I am a very important link!")
    assert e.metadata.link_urls == ["/link"]
    assert e.metadata.link_texts == ["very important link!"]
    e = elements[1]
    assert e == NarrativeText("Here is a list of my favorite things")
    assert e.metadata.link_urls is None
    assert e.metadata.link_texts is None
    e = elements[2]
    assert e == ListItem("Parrots")
    assert e.metadata.link_urls == ["https://en.wikipedia.org/wiki/Parrot"]
    assert e.metadata.link_texts == ["Parrots"]
    e = elements[3]
    assert e == ListItem("Dogs")
    assert e.metadata.link_urls is None
    assert e.metadata.link_texts is None
    e = elements[4]
    assert e == Title("A lone link!")
    assert e.metadata.link_urls == ["/loner"]
    assert e.metadata.link_texts == ["A lone link!"]


def test_partition_html_links():
    elements = partition_html(
        text=(
            "<html>\n"
            '  <a href="/loner">A lone link!</a>\n'
            '  <p>Hello <a href="/link">link!</a></p>\n'
            '  <p>\n   Hello <a href="/link">link!</a></p>\n'
            '  <p><a href="/wiki/parrots">Parrots</a> and <a href="/wiki/dogs">Dogs</a></p>\n'
            "</html>\n"
        )
    )

    e = elements[0]
    assert e.metadata.link_texts == ["A lone link!"]
    assert e.metadata.link_urls == ["/loner"]
    assert e.metadata.link_start_indexes == [-1]
    e = elements[1]
    assert e.metadata.link_texts == ["link!"]
    assert e.metadata.link_urls == ["/link"]
    assert e.metadata.link_start_indexes == [6]
    e = elements[2]
    assert e.metadata.link_texts == ["link!"]
    assert e.metadata.link_urls == ["/link"]
    assert e.metadata.link_start_indexes == [6]
    e = elements[3]
    assert e.metadata.link_texts == ["Parrots", "Dogs"]
    assert e.metadata.link_urls == ["/wiki/parrots", "/wiki/dogs"]
    assert e.metadata.link_start_indexes == [0, 12]


# -- miscellaneous -------------------------------------------------------------------------------


def test_partition_html_from_text_works_with_empty_string():
    assert partition_html(text="") == []


def test_partition_html_on_ideas_page():
    elements = partition_html(example_doc_path("ideas-page.html"))

    assert len(elements) == 1
    assert elements[0] == Table(
        "January 2023 ( Someone fed my essays into GPT to make something that could"
        " answer\nquestions based on them, then asked it where good ideas come from.  The\nanswer"
        " was ok, but not what I would have said. This is what I would have said.) The way to get"
        " new ideas is to notice anomalies: what seems strange,\nor missing, or broken? You can"
        " see anomalies in everyday life (much\nof standup comedy is based on this), but the best"
        " place to look for\nthem is at the frontiers of knowledge. Knowledge grows"
        " fractally.\nFrom a distance its edges look smooth, but when you learn enough\nto get"
        " close to one, you'll notice it's full of gaps. These gaps\nwill seem obvious; it will"
        " seem inexplicable that no one has tried\nx or wondered about y. In the best case,"
        " exploring such gaps yields\nwhole new fractal buds.",
    )
    assert elements[0].metadata.emphasized_text_contents is None
    assert elements[0].metadata.link_urls is None
    assert elements[0].metadata.text_as_html is not None


def test_partition_html_returns_html_elements():
    elements = partition_html(example_doc_path("example-10k-1p.html"))

    assert len(elements) > 0
    assert isinstance(elements[0], HTMLTable)


def test_partition_html_round_trips_through_json():
    elements = partition_html(example_doc_path("example-10k-1p.html"))
    assert_round_trips_through_JSON(elements)


def test_user_without_file_write_permission_can_partition_html(
    tmp_path: pathlib.Path, monkeypatch: MonkeyPatch
):
    read_only_file_path = tmp_path / "example-10k-readonly.html"
    read_only_file_path.write_text(example_doc_text("example-10k-1p.html"))
    read_only_file_path.chmod(0o444)

    elements = partition_html(filename=str(read_only_file_path.resolve()))

    assert len(elements) > 0


# -- module-level fixtures -----------------------------------------------------------------------


EXPECTED_OUTPUT_LANGUAGE_DE = [
    Title(text="Jahresabschluss zum Geschäftsjahr vom 01.01.2020 bis zum 31.12.2020"),
]


@pytest.fixture
def get_last_modified_date_(request: pytest.FixtureRequest):
    return function_mock(request, "unstructured.partition.html.get_last_modified_date")


@pytest.fixture
def get_last_modified_date_from_file_(request: pytest.FixtureRequest):
    return function_mock(request, "unstructured.partition.html.get_last_modified_date_from_file")


class FakeResponse:
    def __init__(self, text: str, status_code: int, headers: dict[str, str] = {}):
        self.text = text
        self.status_code = status_code
        self.ok = status_code < 300
        self.headers = headers


@pytest.fixture
def requests_get_(request: pytest.FixtureRequest):
    return function_mock(request, "unstructured.partition.html.requests.get")
