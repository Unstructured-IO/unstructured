# pyright: reportPrivateUsage=false

"""Test suite for `unstructured.partition.html.partition` module."""

from __future__ import annotations

import io
import pathlib
from typing import Any

import pytest
from lxml import etree

from test_unstructured.unit_utils import (
    FixtureRequest,
    Mock,
    assert_round_trips_through_JSON,
    example_doc_path,
    example_doc_text,
    function_mock,
)
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import (
    Address,
    CompositeElement,
    ListItem,
    NarrativeText,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.file_utils.encoding import read_txt_file
from unstructured.partition.html import partition_html
from unstructured.partition.html.partition import HtmlPartitionerOptions, _HtmlPartitioner

# ================================================================================================
# SOURCE HTML LOADING BEHAVIORS
# ================================================================================================

# -- document-source (filename, file, text, url) -------------------------------------------------


def test_partition_html_accepts_a_file_path(tmp_path: pathlib.Path):
    file_path = str(tmp_path / "sample-doc.html")
    with open(file_path, "w") as f:
        f.write(
            "<html>\n"
            "  <body>\n"
            "    <h1>A Great and Glorious Section</h1>\n"
            "    <p>Dear Leader is the best. He is such a wonderful engineer!</p>\n"
            "    <p></p>\n"
            "    <p>Another Magnificent paragraph</p>\n"
            "    <p><b>The prior element is a title based on its capitalization patterns!</b></p>\n"
            "    <table>\n"
            "      <tbody>\n"
            "        <tr>\n"
            "          <td><p>I'm in a table</p></td>\n"
            "        </tr>\n"
            "      </tbody>\n"
            "    </table>\n"
            "    <h2>A New Beginning</h2>\n"
            "    <div>Here is the start of a new page.</div>\n"
            "  </body>\n"
            "</html>\n"
        )

    elements = partition_html(file_path)

    assert len(elements) == 7
    assert elements == [
        Title("A Great and Glorious Section"),
        NarrativeText("Dear Leader is the best. He is such a wonderful engineer!"),
        Text("Another Magnificent paragraph"),
        NarrativeText("The prior element is a title based on its capitalization patterns!"),
        Table("I'm in a table"),
        Title("A New Beginning"),
        NarrativeText("Here is the start of a new page."),
    ]
    assert all(e.metadata.filename == "sample-doc.html" for e in elements)


def test_user_without_file_write_permission_can_partition_html(tmp_path: pathlib.Path):
    read_only_file_path = tmp_path / "example-10k-readonly.html"
    read_only_file_path.write_text(example_doc_text("example-10k-1p.html"))
    read_only_file_path.chmod(0o444)

    elements = partition_html(filename=str(read_only_file_path.resolve()))

    assert len(elements) > 0


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
    with pytest.raises(ValueError, match="Exactly one of filename, file, text, or url must be sp"):
        partition_html()


# -- encoding for filename, file, and text -------------------------------------------------------


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
    assert partition_html(text='<html charset="utf-8"><p>Hello &#128512;</p></html>') == [
        Text("Hello 😀")
    ]


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


# ================================================================================================
# PARSING TESTS
# ================================================================================================


def test_partition_html_on_ideas_page():
    elements = partition_html(example_doc_path("ideas-page.html"))

    assert len(elements) == 1
    e = elements[0]
    assert e == Table(
        "January 2023 ( Someone fed my essays into GPT to make something that could answer"
        "\nquestions based on them, then asked it where good ideas come from.  The"
        "\nanswer was ok, but not what I would have said. This is what I would have said.)"
        " The way to get new ideas is to notice anomalies: what seems strange,"
        "\nor missing, or broken? You can see anomalies in everyday life (much"
        "\nof standup comedy is based on this), but the best place to look for"
        "\nthem is at the frontiers of knowledge. Knowledge grows fractally."
        "\nFrom a distance its edges look smooth, but when you learn enough"
        "\nto get close to one, you'll notice it's full of gaps. These gaps"
        "\nwill seem obvious; it will seem inexplicable that no one has tried"
        "\nx or wondered about y. In the best case, exploring such gaps yields"
        "\nwhole new fractal buds.",
    )
    assert e.metadata.emphasized_text_contents is None
    assert e.metadata.link_urls is None
    assert e.metadata.text_as_html is not None


# -- element-suppression behaviors ---------------------------------------------------------------


def test_it_does_not_extract_text_in_script_tags():
    elements = partition_html(example_doc_path("example-with-scripts.html"))
    assert all("function (" not in e.text for e in elements)


def test_it_does_not_extract_text_in_style_tags():
    html_text = (
        "<html>\n"
        "<body>\n"
        "  <p><style> p { margin:0; padding:0; } </style>Lorem ipsum dolor</p>\n"
        "</body>\n"
        "</html>"
    )

    (element,) = partition_html(text=html_text)

    assert isinstance(element, Text)
    assert element.text == "Lorem ipsum dolor"


# -- table parsing behaviors ---------------------------------------------------------------------


def test_it_can_parse_a_bare_bones_table_to_a_Table_element():
    """Bare-bones means no `<thead>`, `<tbody>`, or `<tfoot>` elements."""
    html_text = (
        "<html>\n"
        "<body>\n"
        "  <table>\n"
        "    <tr><td>Lorem</td><td>Ipsum</td></tr>\n"
        "    <tr><td>Ut enim non</td><td>ad minim\nveniam quis</td></tr>\n"
        "  </table>\n"
        "</body>\n"
        "</html>"
    )

    (element,) = partition_html(text=html_text)

    assert isinstance(element, Table)
    # -- table text is joined into a single string; no row or cell boundaries are represented --
    assert element.text == "Lorem Ipsum Ut enim non ad minim\nveniam quis"
    # -- An HTML representation is also available that is longer but represents table structure.
    assert element.metadata.text_as_html == (
        "<table>"
        "<tr><td>Lorem</td><td>Ipsum</td></tr>"
        "<tr><td>Ut enim non</td><td>ad minim<br/>veniam quis</td></tr>"
        "</table>"
    )


def test_it_accommodates_column_heading_cells_enclosed_in_thead_tbody_and_tfoot_elements():
    """Cells within a `table/thead` element are included in the text and html.

    The presence of a `<thead>` element in the original also determines whether a `<thead>` element
    appears in `.text_as_html` or whether the first row of cells is simply in the body.
    """
    html_text = (
        "<html>\n"
        "<body>\n"
        "  <table>\n"
        "    <thead>\n"
        "      <tr><th>Lorem</th><th>Ipsum</th></tr>\n"
        "    </thead>\n"
        "    <tbody>\n"
        "      <tr><th>Lorem ipsum</th><td>dolor sit amet nulla</td></tr>\n"
        "      <tr><th>Ut enim non</th><td>ad minim\nveniam quis</td></tr>\n"
        "    </tbody>\n"
        "    <tfoot>\n"
        "      <tr><th>Dolor</th><td>Equis</td></tr>\n"
        "    </tfoot>\n"
        "  </table>\n"
        "</body>\n"
        "</html>"
    )

    (element,) = partition_html(text=html_text)

    assert isinstance(element, Table)
    assert element.metadata.text_as_html == (
        "<table>"
        "<tr><td>Lorem</td><td>Ipsum</td></tr>"
        "<tr><td>Lorem ipsum</td><td>dolor sit amet nulla</td></tr>"
        "<tr><td>Ut enim non</td><td>ad minim<br/>veniam quis</td></tr>"
        "<tr><td>Dolor</td><td>Equis</td></tr>"
        "</table>"
    )


def test_it_does_not_emit_a_Table_element_for_a_table_with_no_text():
    html_text = (
        "<html>\n"
        "<body>\n"
        "  <table>\n"
        "    <tr><td> </td><td> </td></tr>\n"
        "    <tr><td> </td><td> </td></tr>\n"
        "  </table>\n"
        "</body>\n"
        "</html>"
    )

    assert partition_html(text=html_text) == []


def test_it_provides_parseable_HTML_in_text_as_html():
    html_text = (
        "<html>\n"
        "<body>\n"
        "  <table>\n"
        "    <thead>\n"
        "      <tr><th>Lorem</th><th>Ipsum</th></tr>\n"
        "    </thead>\n"
        "    <tbody>\n"
        "      <tr><th>Lorem ipsum</th><td>dolor sit amet nulla</td></tr>\n"
        "      <tr><th>Ut enim non</th><td>ad minim\nveniam quis</td></tr>\n"
        "    </tbody>\n"
        "    <tfoot>\n"
        "      <tr><th>Dolor</th><td>Equis</td></tr>\n"
        "    </tfoot>\n"
        "  </table>\n"
        "</body>\n"
        "</html>"
    )

    (element,) = partition_html(text=html_text)

    text_as_html = element.metadata.text_as_html
    assert text_as_html is not None

    html = etree.fromstring(text_as_html, etree.HTMLParser())

    assert html is not None
    # -- lxml adds the <html><body> container, that's not present in `.text_as_html` --
    assert etree.tostring(html, encoding=str) == (
        "<html><body>"
        "<table>"
        "<tr><td>Lorem</td><td>Ipsum</td></tr>"
        "<tr><td>Lorem ipsum</td><td>dolor sit amet nulla</td></tr>"
        "<tr><td>Ut enim non</td><td>ad minim<br/>veniam quis</td></tr>"
        "<tr><td>Dolor</td><td>Equis</td></tr>"
        "</table>"
        "</body></html>"
    )


@pytest.mark.parametrize(
    ("tag", "expected_text_as_html"),
    [
        ("thead", "<table><tr><td>Header 1</td><td>Header 2</td></tr></table>"),
        ("tfoot", "<table><tr><td>Header 1</td><td>Header 2</td></tr></table>"),
    ],
)
def test_partition_html_parses_table_without_tbody(tag: str, expected_text_as_html: str):
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


def test_partition_html_reduces_a_nested_table_to_its_text_placed_in_the_cell_that_contains_it():
    html_text = (
        "<table>\n"
        " <tr>\n"
        "  <td>\n"
        "   <table>\n"
        "     <tr><td>foo</td><td>bar</td></tr>\n"
        "     <tr><td>baz</td><td>bng</td></tr>\n"
        "   </table>\n"
        "  </td>\n"
        "  <td>\n"
        "   <table>\n"
        "     <tr><td>fizz</td><td>bang</td></tr>\n"
        "   </table>\n"
        "  </td>\n"
        " </tr>\n"
        "</table>"
    )

    (element,) = partition_html(text=html_text)

    assert element == Table("foo bar baz bng fizz bang")
    assert element.metadata.text_as_html == (
        "<table><tr><td>foo bar baz bng</td><td>fizz bang</td></tr></table>"
    )


def test_partition_html_accommodates_tds_with_child_elements():
    """Like this example from an SEC 10k filing."""
    html_text = (
        "<table>\n"
        " <tr>\n"
        "  <td></td>\n"
        "  <td></td>\n"
        " </tr>\n"
        " <tr>\n"
        "  <td>\n"
        "   <p>\n"
        "    <span>\n"
        '     <ix:nonNumeric id="F_be4cc145-372a-4689-be60-d8a70b0c8b9a"'
        ' contextRef="C_1de69f73-df01-4830-8af0-0f11b469bc4a" name="dei:DocumentAnnualReport"'
        ' format="ixt-sec:boolballotbox">\n'
        "     <span>&#9746;</span>\n"
        "     </ix:nonNumeric>\n"
        "    </span>\n"
        "   </p>\n"
        "  </td>\n"
        "  <td>\n"
        "   <p>\n"
        "    <span>ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE"
        " ACT OF 1934</span>\n"
        "   </p>\n"
        "  </td>\n"
        " </tr>\n"
        "</table>\n"
    )

    (element,) = partition_html(text=html_text)

    assert element == Table(
        "☒ ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934"
    )
    assert element.metadata.text_as_html == (
        "<table>"
        "<tr><td/><td/></tr>"
        "<tr><td>☒</td><td>ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES"
        " EXCHANGE ACT OF 1934</td></tr>"
        "</table>"
    )


# -- other element-specific behaviors ------------------------------------------------------------


def test_partition_html_recognizes_h1_to_h6_as_Title_with_category_depth():
    html_text = (
        "<p>This is narrative text, it's long, flows and has meaning</p>\n"
        "<h1>This heading is a title, even though it's long, flows and has meaning</h1>\n"
        "<h2>A heading that is at the second level</h2>\n"
        "<h3>Finally, the third heading</h3>\n"
        "<h4>December 1-17, 2017</h4>\n"
        "<h5>email@example.com</h5>\n"
        "<h6>* bullet point</h6>\n"
        "<h3><li>- invalidly nested list item</li></h3>\n"
    )

    elements = partition_html(text=html_text)

    assert len(elements) == 8
    e = elements[0]
    assert e == NarrativeText("This is narrative text, it's long, flows and has meaning")
    assert e.metadata.category_depth is None
    e = elements[1]
    assert e == Title("This heading is a title, even though it's long, flows and has meaning")
    assert e.metadata.category_depth == 0
    e = elements[2]
    assert e == Title("A heading that is at the second level")
    assert e.metadata.category_depth == 1
    e = elements[3]
    assert e == Title("Finally, the third heading")
    assert e.metadata.category_depth == 2
    e = elements[4]
    assert e == Title("December 1-17, 2017")
    assert e.metadata.category_depth == 3
    e = elements[5]
    assert e == Title("email@example.com")
    assert e.metadata.category_depth == 4
    e = elements[6]
    assert e == Title("* bullet point")
    assert e.metadata.category_depth == 5
    e = elements[7]
    assert e == ListItem("- invalidly nested list item")
    assert e.metadata.category_depth == 0


def test_partition_html_with_widely_encompassing_pre_tag():
    elements = partition_html(example_doc_path("fake-html-pre.htm"))

    print(f"{len(elements)=}")
    assert len(elements) > 0
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
        Text("The Big Brown Bear"),
        NarrativeText("The big brown bear is growling."),
        NarrativeText("The big brown bear is sleeping."),
        Text("The Big Blue Bear"),
    ]


def test_partition_html_br_tag_parsing():
    html_text = (
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

    elements = partition_html(text=html_text)

    assert elements == [
        Title("Header 1"),
        Text("Text"),
        Title("Header 2"),
        Text(
            "    Param1 = Y\nParam2 = 1\nParam3 = 2\nParam4 = A\n    \nParam5 = A,B,C,D,E\n"
            "Param6 = 7\nParam7 = Five\n\n  "
        ),
    ]

    e = elements[3]
    assert e.metadata.emphasized_text_contents == [
        "Param1",
        "Param2",
        "Param3",
        "Param4",
        "Param5",
        "Param6",
        "Param7",
    ]
    assert e.metadata.emphasized_text_tags == ["b", "b", "b", "b", "b", "b", "b"]


def test_partition_html_tag_tail_parsing():
    html_text = (
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

    elements = partition_html(text=html_text)

    assert elements == [Text("Head"), Text("Nested"), Text("Tail")]


# -- parsing edge cases --------------------------------------------------------------------------


def test_partition_html_from_text_works_with_empty_string():
    assert partition_html(text="") == []


def test_partition_html_accommodates_block_item_nested_inside_phrasing_element():
    html_text = """
    <div>
      We start out normally
      <cite>
        and then add a citation
        <p>But whoa, this is a paragraph inside a phrasing element.</p>
        so we close the first element at the start of the block element and emit it, then we
        <b>emit</b> the block element,
      </cite>
      and then start a new element for the tail and whatever phrasing follows it.
    </div>
    """

    elements = partition_html(text=html_text)

    assert elements == [
        NarrativeText("We start out normally and then add a citation"),
        NarrativeText("But whoa, this is a paragraph inside a phrasing element."),
        NarrativeText(
            "so we close the first element at the start of the block element and emit it,"
            " then we emit the block element,"
            " and then start a new element for the tail and whatever phrasing follows it."
        ),
    ]
    assert elements[2].metadata.emphasized_text_contents == ["emit"]
    assert elements[2].metadata.emphasized_text_tags == ["b"]


def test_partition_html_handles_anchor_with_nested_block_item():
    html_text = """
    <div>
      O Deep Thought
      <a href="http://eie.io">
        computer, he said,
        <p>The task we have designed you to perform is this.</p>
        We want you to tell us....
      </a>
      he paused,
    </div>
    """

    elements = partition_html(text=html_text)

    assert [e.text for e in elements] == [
        "O Deep Thought computer, he said,",
        "The task we have designed you to perform is this.",
        "We want you to tell us.... he paused,",
    ]
    link_annotated_element = elements[0]
    assert link_annotated_element.metadata.link_texts == ["computer, he said,"]
    assert link_annotated_element.metadata.link_urls == ["http://eie.io"]
    assert all(e.metadata.link_texts is None for e in elements[1:])
    assert all(e.metadata.link_urls is None for e in elements[1:])


def test_containers_with_text_are_processed():
    html_text = (
        '<div dir=3D"ltr">Hi All,\n'
        "  <div><br></div>\n"
        "  <div>Get excited for our first annual family day!</div>\n"
        '  <div>Best.<br clear="all">\n'
        "    <div><br></div>\n"
        "    -- <br>\n"
        '    <div dir=3D"ltr">\n'
        '      <div dir=3D"ltr">Dino the Datasaur<div>\n'
        "      Unstructured Technologies<br>\n"
        "      <div>Data Scientist</div>\n"
        "      <div>Doylestown, PA 18901</div>\n"
        "      <div><br></div>\n"
        "    </div>\n"
        "  </div>\n"
        "  See you there!\n"
        "</div>\n"
    )

    elements = partition_html(text=html_text)

    assert elements == [
        Text("Hi All,"),
        NarrativeText("Get excited for our first annual family day!"),
        Text("Best."),
        Text("--"),
        Text("Dino the Datasaur"),
        Text("Unstructured Technologies"),
        Text("Data Scientist"),
        Address("Doylestown, PA 18901"),
        NarrativeText("See you there!"),
    ]


def test_html_grabs_bulleted_text_in_tags():
    html_text = (
        "<html>\n"
        "  <body>\n"
        "    <ol>\n"
        "      <li>Happy Groundhog's day!</li>\n"
        "      <li>Looks like six more weeks of winter ...</li>\n"
        "    </ol>\n"
        "  </body>\n"
        "</html>\n"
    )

    elements = partition_html(text=html_text)

    assert elements == [
        ListItem("Happy Groundhog's day!"),
        ListItem("Looks like six more weeks of winter ..."),
    ]


def test_html_grabs_bulleted_text_in_paras():
    html_text = (
        "<html>\n"
        "  <body>\n"
        "    <p>\n"
        "      <span>&#8226; Happy Groundhog's day!</span>\n"
        "    </p>\n"
        "    <p>\n"
        "      <span>&#8226; Looks like six more weeks of winter ...</span>\n"
        "    </p>\n"
        "  </body>\n"
        "</html>\n"
    )

    elements = partition_html(text=html_text)

    # -- bullet characters are removed --
    assert elements == [
        ListItem("Happy Groundhog's day!"),
        ListItem("Looks like six more weeks of winter ..."),
    ]


def test_joins_tag_text_correctly():
    elements = partition_html(text="<p>Hello again peet mag<i>ic</i>al</p>")
    assert elements == [Text("Hello again peet magical")]


def test_sample_doc_with_emoji():
    elements = partition_html(text='<html charset="unicode">\n<p>Hello again 😀</p>\n</html>')
    assert elements == [NarrativeText("Hello again 😀")]


def test_only_text_and_no_elements_in_body():
    elements = partition_html(text="<body>Hello</body>")
    assert elements == [Text("Hello")]


def test_text_before_elements_in_body():
    elements = partition_html(text="<body>Hello<p>World</p></body>")
    assert elements == [Text("Hello"), Text("World")]


def test_line_break_in_container():
    elements = partition_html(text="<div>Hello<br/>World</div>")
    assert elements == [Text("Hello World")]


@pytest.mark.parametrize("tag", ["del", "form", "noscript"])
def test_exclude_tag_types(tag: str):
    html_text = f"<body>\n  <{tag}>\n    There is some text here.\n  </{tag}>\n</body>\n"

    elements = partition_html(text=html_text)

    assert elements == []


# ================================================================================================
# OTHER ARGS
# ================================================================================================

# -- `chunking_strategy` arg ---------------------------------------------------------------------


def test_partition_html_can_chunk_while_partitioning():
    file_path = example_doc_path("example-10k-1p.html")
    chunks = partition_html(file_path, chunking_strategy="by_title")
    chunks_2 = chunk_by_title(partition_html(file_path))
    assert all(isinstance(c, (CompositeElement, Table, TableChunk)) for c in chunks)
    assert chunks == chunks_2


# -- `skip_headers_and_footers` arg --------------------------------------------------------------


def test_partition_html_can_skip_headers_and_footers():
    assert partition_html(
        text=(
            "<html>\n"
            "  <header>\n"
            "    <p>Header</p>\n"
            "  </header>\n"
            "  <body>\n"
            "    <h1>My First Heading</h1>\n"
            "    <p>It was a dark and stormy night. No one was around.</p>\n"
            "  </body>\n"
            "  <footer>\n"
            "    <p>Footer</p>\n"
            "  </footer>\n"
            "</html>\n"
        ),
        skip_headers_and_footers=True,
    ) == [
        Title("My First Heading"),
        NarrativeText("It was a dark and stormy night. No one was around."),
    ]


# -- `unique_element_ids` arg --------------------------------------------------------------------


def test_all_element_ids_are_unique():
    ids = [e.id for e in partition_html(example_doc_path("fake-html-with-duplicate-elements.html"))]
    assert len(ids) == len(set(ids))


def test_element_ids_are_deterministic():
    ids = [e.id for e in partition_html("example-docs/fake-html-with-duplicate-elements.html")]
    ids_2 = [e.id for e in partition_html("example-docs/fake-html-with-duplicate-elements.html")]
    assert ids == ids_2


# ================================================================================================
# METADATA BEHAVIORS
# ================================================================================================

# -- .metadata.category_depth + parent_id --------------------------------------------------------


def test_partition_html_records_hierarchy_metadata():
    elements = partition_html(
        text=(
            "<html>\n"
            "  <p>Preamble gets no category_depth or parent_id</p>\n"
            "  <h1>Heading gets category_depth but no parent_id</h1>\n"
            "  <p>Body paragraph gets parent_id but no category_depth</p>\n"
            "  <ul>\n"
            "    <li>List item gets category_depth and parent_id</li>\n"
            "    <li>Second list item gets category_depth and parent_id</li>\n"
            "  </ul>\n"
            "  <p>Body paragraph after list gets parent_id but no category_depth</p>\n"
            "</html>\n"
        )
    )

    assert len(elements) == 6
    e = elements[0]
    assert isinstance(e, NarrativeText)
    assert e.text == "Preamble gets no category_depth or parent_id"
    assert e.metadata.category_depth is None
    assert e.metadata.parent_id is None
    e = elements[1]
    assert isinstance(e, Title)
    assert e.text == "Heading gets category_depth but no parent_id"
    assert e.metadata.category_depth == 0
    assert e.metadata.parent_id is None
    e = elements[2]
    assert isinstance(e, NarrativeText)
    assert e.text == "Body paragraph gets parent_id but no category_depth"
    assert e.metadata.category_depth is None
    assert e.metadata.parent_id == elements[1].id
    e = elements[3]
    assert isinstance(e, ListItem)
    assert e.text == "List item gets category_depth and parent_id"
    assert e.metadata.category_depth == 1
    assert e.metadata.parent_id == elements[1].id
    e = elements[4]
    assert isinstance(e, ListItem)
    assert e.text == "Second list item gets category_depth and parent_id"
    assert e.metadata.category_depth == 1
    assert e.metadata.parent_id == elements[1].id
    e = elements[5]
    assert isinstance(e, NarrativeText)
    assert e.text == "Body paragraph after list gets parent_id but no category_depth"
    assert e.metadata.category_depth is None
    assert e.metadata.parent_id == elements[1].id


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
    assert e.metadata.emphasized_text_tags == ["b"]
    e = elements[1]
    assert e == NarrativeText("Here is a list of my favorite things")
    assert e.metadata.emphasized_text_contents == ["my", "favorite", "things"]
    assert e.metadata.emphasized_text_tags == ["b", "bi", "b"]
    e = elements[2]
    assert e == ListItem("Parrots")
    assert e.metadata.emphasized_text_contents == ["Parrots"]
    assert e.metadata.emphasized_text_tags == ["i"]
    e = elements[3]
    assert e == ListItem("Dogs")
    assert e.metadata.emphasized_text_contents is None
    assert e.metadata.emphasized_text_tags is None
    e = elements[4]
    assert e == Text("A lone span text!")
    assert e.metadata.emphasized_text_contents is None
    assert e.metadata.emphasized_text_tags is None


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_html_from_filename_uses_source_filename_for_metadata_by_default():
    elements = partition_html(example_doc_path("example-10k-1p.html"))

    assert len(elements) > 0
    assert all(e.metadata.filename == "example-10k-1p.html" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("") for e in elements)


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


def test_partition_html_from_filename_pulls_last_modified_from_filesystem(request: FixtureRequest):
    get_last_modified_date_ = function_mock(
        request,
        "unstructured.partition.html.partition.get_last_modified_date",
        return_value="2024-06-17T22:22:20",
    )
    file_path = example_doc_path("fake-html.html")

    elements = partition_html(file_path)

    get_last_modified_date_.assert_called_once_with(file_path)
    assert elements
    assert all(e.metadata.last_modified == "2024-06-17T22:22:20" for e in elements)


def test_partition_html_from_filename_prefers_metadata_last_modified():
    elements = partition_html(
        example_doc_path("fake-html.html"), metadata_last_modified="2023-07-05T09:24:28"
    )

    assert isinstance(elements[0], Title)
    assert all(e.metadata.last_modified == "2023-07-05T09:24:28" for e in elements)


# -- .metadata.link_texts and .link_urls ---------------------------------------------------------


def test_partition_html_grabs_links():
    html_text = (
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

    elements = partition_html(text=html_text)

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
    assert e == Text("A lone link!")
    assert e.metadata.link_urls == ["/loner"]
    assert e.metadata.link_texts == ["A lone link!"]


def test_partition_html_links():
    html_text = (
        "<html>\n"
        '  <a href="/loner">A lone link!</a>\n'
        '  <p>Hello <a href="/link">link!</a></p>\n'
        '  <p>\n   Hello <a href="/link">link!</a></p>\n'
        '  <p><a href="/wiki/parrots">Parrots</a> and <a href="/wiki/dogs">Dogs</a></p>\n'
        "</html>\n"
    )

    elements = partition_html(text=html_text)

    e = elements[0]
    assert e.metadata.link_texts == ["A lone link!"]
    assert e.metadata.link_urls == ["/loner"]
    e = elements[1]
    assert e.metadata.link_texts == ["link!"]
    assert e.metadata.link_urls == ["/link"]
    e = elements[2]
    assert e.metadata.link_texts == ["link!"]
    assert e.metadata.link_urls == ["/link"]
    e = elements[3]
    assert e.metadata.link_texts == ["Parrots", "Dogs"]
    assert e.metadata.link_urls == ["/wiki/parrots", "/wiki/dogs"]


# -- .metadata.text_as_html ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("html_text", "expected_value"),
    [
        (
            "<table><tr><th>Header 1</th><th>Header 2</th></tr></table>",
            "<table><tr><td>Header 1</td><td>Header 2</td></tr></table>",
        ),
        (
            "<table>"
            "<tr><td>Dimensions</td><td>Weight</td></tr>"
            "<tr><td>4'-6\" x 1'</td><td>18 kg</td></tr>"
            "</table>",
            # ----------
            "<table>"
            "<tr><td>Dimensions</td><td>Weight</td></tr>"
            "<tr><td>4&#x27;-6&quot; x 1&#x27;</td><td>18 kg</td></tr>"
            "</table>",
        ),
    ],
)
def test_partition_html_applies_text_as_html_metadata_for_tables(
    html_text: str, expected_value: str
):
    elements = partition_html(text=html_text)

    assert len(elements) == 1
    assert elements[0].metadata.text_as_html == expected_value


# -- .metadata.url -------------------------------------------------------------------------------


def test_partition_html_from_url_adds_url_to_metadata(requests_get_: Mock):
    requests_get_.return_value = FakeResponse(
        text=example_doc_text("example-10k-1p.html"),
        status_code=200,
        headers={"Content-Type": "text/html"},
    )

    elements = partition_html(url="https://trusttheforceluke.com")

    requests_get_.assert_called_once_with("https://trusttheforceluke.com", headers={}, verify=True)
    assert len(elements) > 0
    assert all(e.metadata.url == "https://trusttheforceluke.com" for e in elements)


# ================================================================================================
# SERIALIZATION BEHAVIORS
# ================================================================================================


def test_partition_html_round_trips_through_json():
    elements = partition_html(example_doc_path("example-10k-1p.html"))
    assert_round_trips_through_JSON(elements)


# ================================================================================================
# MODULE-LEVEL FIXTURES
# ================================================================================================

EXPECTED_OUTPUT_LANGUAGE_DE = [
    Title(text="Jahresabschluss zum Geschäftsjahr vom 01.01.2020 bis zum 31.12.2020"),
]


class FakeResponse:
    def __init__(self, text: str, status_code: int, headers: dict[str, str] = {}):
        self.text = text
        self.status_code = status_code
        self.ok = status_code < 300
        self.headers = headers


@pytest.fixture
def opts_args() -> dict[str, Any]:
    """All default arguments for `HtmlPartitionerOptions`.

    Individual argument values can be changed to suit each test. Makes construction of opts more
    compact for testing purposes.
    """
    return {
        "file": None,
        "file_path": None,
        "text": None,
        "encoding": None,
        "url": None,
        "headers": {},
        "ssl_verify": True,
        "skip_headers_and_footers": False,
        "detection_origin": None,
    }


@pytest.fixture
def requests_get_(request: pytest.FixtureRequest):
    return function_mock(request, "unstructured.partition.html.partition.requests.get")


# ================================================================================================
# ISOLATED UNIT TESTS
# ================================================================================================
# These test components used by `partition_html()` in isolation such that all edge cases can be
# exercised.
# ================================================================================================


class DescribeHtmlPartitionerOptions:
    """Unit-test suite for `unstructured.partition.html.partition.HtmlPartitionerOptions`."""

    # -- .detection_origin -----------------------

    @pytest.mark.parametrize("detection_origin", ["html", None])
    def it_knows_the_caller_provided_detection_origin(
        self, detection_origin: str | None, opts_args: dict[str, Any]
    ):
        opts_args["detection_origin"] = detection_origin
        opts = HtmlPartitionerOptions(**opts_args)

        assert opts.detection_origin == detection_origin

    # -- .html_text ------------------------------

    def it_gets_the_HTML_from_the_file_path_when_one_is_provided(self, opts_args: dict[str, Any]):
        file_path = example_doc_path("example-10k-1p.html")
        opts_args["file_path"] = file_path
        opts = HtmlPartitionerOptions(**opts_args)

        html_text = opts.html_text

        assert isinstance(html_text, str)
        assert html_text == read_txt_file(file_path)[1]

    def and_it_gets_the_HTML_from_the_file_like_object_when_one_is_provided(
        self, opts_args: dict[str, Any]
    ):
        file_path = example_doc_path("example-10k-1p.html")
        with open(file_path, "rb") as f:
            file = io.BytesIO(f.read())
        opts_args["file"] = file
        opts = HtmlPartitionerOptions(**opts_args)

        html_text = opts.html_text

        assert isinstance(html_text, str)
        assert html_text == read_txt_file(file_path)[1]

    def and_it_uses_the_HTML_in_the_text_argument_when_that_is_provided(
        self, opts_args: dict[str, Any]
    ):
        opts_args["text"] = "<html><body><p>Hello World!</p></body></html>"
        opts = HtmlPartitionerOptions(**opts_args)

        assert opts.html_text == "<html><body><p>Hello World!</p></body></html>"

    def and_it_gets_the_HTML_from_the_url_when_one_is_provided(
        self, requests_get_: Mock, opts_args: dict[str, Any]
    ):
        requests_get_.return_value = FakeResponse(
            text="<html><body><p>I just flew over the internet!</p></body></html>",
            status_code=200,
            headers={"Content-Type": "text/html"},
        )
        opts_args["url"] = "https://insta.tweet.face.org"
        opts = HtmlPartitionerOptions(**opts_args)

        assert opts.html_text == "<html><body><p>I just flew over the internet!</p></body></html>"

    def but_it_raises_when_no_path_or_file_or_text_or_url_was_provided(
        self, opts_args: dict[str, Any]
    ):
        opts = HtmlPartitionerOptions(**opts_args)

        with pytest.raises(ValueError, match="Exactly one of filename, file, text, or url must be"):
            opts.html_text

    # -- .last_modified --------------------------

    def it_gets_last_modified_from_the_filesystem_when_file_path_is_provided(
        self, opts_args: dict[str, Any], get_last_modified_date_: Mock
    ):
        opts_args["file_path"] = "a/b/document.html"
        get_last_modified_date_.return_value = "2024-04-02T20:32:35"
        opts = HtmlPartitionerOptions(**opts_args)

        last_modified = opts.last_modified

        get_last_modified_date_.assert_called_once_with("a/b/document.html")
        assert last_modified == "2024-04-02T20:32:35"

    def but_it_falls_back_to_None_for_the_last_modified_date_when_no_file_path_is_provided(
        self, opts_args: dict[str, Any]
    ):
        file = io.BytesIO(b"abcdefg")
        opts_args["file"] = file
        opts = HtmlPartitionerOptions(**opts_args)

        last_modified = opts.last_modified

        assert last_modified is None

    # -- .skip_headers_and_footers ---------------

    @pytest.mark.parametrize("skip_headers_and_footers", [True, False])
    def it_knows_the_caller_provided_skip_headers_and_footers_setting(
        self, skip_headers_and_footers: bool, opts_args: dict[str, Any]
    ):
        opts_args["skip_headers_and_footers"] = skip_headers_and_footers
        opts = HtmlPartitionerOptions(**opts_args)

        assert opts.skip_headers_and_footers is skip_headers_and_footers

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def get_last_modified_date_(self, request: FixtureRequest) -> Mock:
        return function_mock(
            request, "unstructured.partition.html.partition.get_last_modified_date"
        )


class Describe_HtmlPartitioner:
    """Unit-test suite for `unstructured.partition.html.partition._HtmlPartitioner`."""

    # -- ._main ----------------------------------

    def it_can_find_the_main_element_in_the_document(self, opts_args: dict[str, Any]):
        opts_args["text"] = (
            "<body>\n"
            "  <header></header>\n"
            "  <p>Lots preamble stuff yada yada yada</p>\n"
            "  <main>\n"
            "    <h2>A Wonderful Section!</h2>\n"
            "    <p>Look at this amazing section!</p>\n"
            "  </main>\n"
            "</body>\n"
        )
        opts = HtmlPartitionerOptions(**opts_args)

        partitioner = _HtmlPartitioner(opts)

        assert partitioner._main.tag == "main"

    def and_it_falls_back_to_the_body_when_there_is_no_main(self, opts_args: dict[str, Any]):
        """And there is always a <body>, the parser adds one if there's not one in the HTML."""
        opts_args["text"] = (
            "<body>\n"
            "  <header></header>\n"
            "  <p>Lots preamble stuff yada yada yada</p>\n"
            "  <h2>A Wonderful Section!</h2>\n"
            "  <p>Look at this amazing section!</p>\n"
            "</body>\n"
        )
        opts = HtmlPartitionerOptions(**opts_args)

        partitioner = _HtmlPartitioner(opts)

        assert partitioner._main.tag == "body"

    # -- ElementCls selection behaviors -----------------

    def it_produces_a_Text_element_when_the_tag_contents_are_not_narrative_or_a_title(
        self, opts_args: dict[str, Any]
    ):
        opts_args["text"] = "<p>NO PARTICULAR TYPE.</p>"
        opts = HtmlPartitionerOptions(**opts_args)

        (element,) = list(_HtmlPartitioner.iter_elements(opts))

        assert element == Text("NO PARTICULAR TYPE.")

    def it_produces_a_ListItem_element_when_the_tag_contains_are_preceded_by_a_bullet_character(
        self, opts_args: dict[str, Any]
    ):
        opts_args["text"] = "<p>● An excellent point!</p>"
        opts = HtmlPartitionerOptions(**opts_args)

        (element,) = list(_HtmlPartitioner.iter_elements(opts))

        assert element == ListItem("An excellent point!")

    def but_not_when_the_tag_contains_only_a_bullet_character_and_no_text(
        self, opts_args: dict[str, Any]
    ):
        opts_args["text"] = "<p>●</p>"
        opts = HtmlPartitionerOptions(**opts_args)

        assert list(_HtmlPartitioner.iter_elements(opts)) == []

    def it_produces_no_element_when_the_tag_has_no_content(self, opts_args: dict[str, Any]):
        opts_args["text"] = "<p></p>"
        opts = HtmlPartitionerOptions(**opts_args)

        assert list(_HtmlPartitioner.iter_elements(opts)) == []

    def and_it_produces_no_element_when_the_tag_contains_only_a_stub(
        self, opts_args: dict[str, Any]
    ):
        opts_args["text"] = "<p>$</p>"
        opts = HtmlPartitionerOptions(**opts_args)

        assert list(_HtmlPartitioner.iter_elements(opts)) == []
