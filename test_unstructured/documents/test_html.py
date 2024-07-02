# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

"""Test suite for `unstructured.documents.html` module."""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
from lxml import etree

from test_unstructured.unit_utils import (
    FixtureRequest,
    Mock,
    function_mock,
    property_mock,
)
from unstructured.documents import html
from unstructured.documents.elements import (
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
)
from unstructured.documents.html import HTMLDocument
from unstructured.partition.html.partition import HtmlPartitionerOptions

TAGS = (
    (
        "<a><abbr><acronym><address><applet><area><article><aside><audio><b><base><basefont><bdi>"
        "<bdo><big><blockquote><body><br><button><canvas><caption><center><cite><code><col>"
        "<colgroup><data><datalist><dd><del><details><dfn><dialog><dir><div><dl><dt><em><embed>"
        "<fieldset><figcaption><figure><font><footer><form><frame><frameset><h1><h2><h3><h4><h5>"
        "<h6><head><header><hr><html><i><iframe><img><input><ins><kbd><label><legend><li><link>"
        "<main><map><mark><meta><meter><nav><noframes><noscript><object><ol><optgroup><option>"
        "<output><p><param><picture><pre><progress><q><rp><rt><ruby><s><samp><script><section>"
        "<select><small><source><span><strike><strong><style><sub><summary><sup><table><tbody><td>"
        "<template><textarea><tfoot><th><thead><time><title><tr><track><tt><u><ul><var><video><wbr>"
    )
    .replace(">", "")
    .split("<")[1:]
)

VOID_TAGS = (
    ("<area><base><br><col><embed><hr><img><input><link><meta><param><source><track><wbr>")
    .replace(">", "")
    .split("<")[1:]
)

INCLUDED_TAGS = html.TEXT_TAGS + html.HEADING_TAGS + html.LIST_ITEM_TAGS + html.SECTION_TAGS
EXCLUDED_TAGS = [
    tag
    for tag in TAGS
    if tag not in (INCLUDED_TAGS + html.TABLE_TAGS + VOID_TAGS + ["html", "head", "body"])
]


# -- HTMLDocument.from_file() --------------------------------------------------------------------


def test_read_html_doc(tmp_path: pathlib.Path, opts_args: dict[str, Any]):
    file_path = str(tmp_path / "sample-doc.html")
    with open(file_path, "w") as f:
        f.write(
            "<html>\n"
            "  <body>\n"
            "    <h1>A Great and Glorious Section</h1>\n"
            "    <p>Dear Leader is the best. He is such a wonderful engineer!</p>\n"
            "    <p></p>\n"
            "    <p>Another Magnificent Title</p>\n"
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
    opts_args["file_path"] = file_path
    opts = HtmlPartitionerOptions(**opts_args)

    elements = HTMLDocument.load(opts).elements

    assert len(elements) == 7
    assert elements == [
        Title("A Great and Glorious Section"),
        NarrativeText("Dear Leader is the best. He is such a wonderful engineer!"),
        Title("Another Magnificent Title"),
        NarrativeText("The prior element is a title based on its capitalization patterns!"),
        Table("I'm in a table"),
        Title("A New Beginning"),
        NarrativeText("Here is the start of a new page."),
    ]


# -- HTMLDocument.elements -----------------------------------------------------------------------


@pytest.mark.parametrize("tag", html.TEXT_TAGS)
def test_line_break_in_text_tag(tag: str, opts_args: dict[str, Any]):
    opts_args["text"] = f"<{tag}>Hello<br/>World</{tag}>"
    opts = HtmlPartitionerOptions(**opts_args)
    doc = HTMLDocument.load(opts)
    assert doc.elements[0].text == "Hello"
    assert doc.elements[1].text == "World"


@pytest.mark.parametrize("tag", [tag for tag in html.TEXT_TAGS if tag not in html.TABLE_TAGS])
def test_tag_types(tag: str, opts_args: dict[str, Any]):
    opts_args["text"] = f"<body>\n  <{tag}>\n    There is some text here.\n  </{tag}>\n</body>\n"
    opts = HtmlPartitionerOptions(**opts_args)

    elements = HTMLDocument.load(opts).elements

    assert len(elements) == 1


# -- _construct_text() ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("doc", "expected"),
    [
        (
            "<p>Hi there <span>my name is</span> <b><i>Matt</i></i></p>",
            "Hi there my name is Matt",
        ),
        ("<p>I have a</p> tail", "I have a tail"),
    ],
)
def test_construct_text(doc: str, expected: str):
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    para = document_tree.find(".//p")
    assert para is not None
    text = html._construct_text(para)
    assert text == expected


# -- _get_emphasized_texts_from_tag() ------------------------------------------------------------


@pytest.mark.parametrize(
    ("doc", "root", "expected"),
    [
        (
            "<p>Hello <strong>there</strong> I <em>am</em> a <b>very</b> <i>important</i> text</p>",
            "p",
            (["there", "am", "very", "important"], ["strong", "em", "b", "i"]),
        ),
        (
            "<p>Here is a <span>list</span> of <b>my <i>favorite</i> things</b></p>",
            "p",
            (["list", "my favorite things", "favorite"], ["span", "b", "i"]),
        ),
        ("<strong>A lone strong text!</strong>", "strong", (["A lone strong text!"], ["strong"])),
        ("<span>I have a</span> tail", "span", (["I have a"], ["span"])),
    ],
)
def test_get_emphasized_texts_from_tag(doc: str, root: str, expected: list[dict[str, str]]):
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(f".//{root}")
    assert el is not None

    emphasized_texts = html._get_emphasized_texts_from_tag(el)

    assert emphasized_texts == expected


# -- _get_links_from_tag() -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("doc", "root", "expected"),
    [
        (
            "<a href='/loner'>A lone link!</a>",
            "a",
            (["A lone link!"], ["/loner"], [-1]),
        ),
        (
            "<ul><li><a href='/wiki/Parrot'>Parrots</a></li><li>Dogs</li></ul>",
            "ul",
            (["Parrots"], ["/wiki/Parrot"], [0]),
        ),
        (
            "<ul><li><a href='/parrot'>Parrots</a></li><li><a href='/dog'>Dogs</a></li></ul>",
            "ul",
            (["Parrots", "Dogs"], ["/parrot", "/dog"], [0, 7]),
        ),
        (
            "<div>Here is <p>P tag</p> tail text. <a href='/link'>link!</a></div>",
            "div",
            (["link!"], ["/link"], [25]),
        ),
        (
            "<div>Here is <p>P tag</p><a href='/link'>link!</a></div>",
            "div",
            (["link!"], ["/link"], [13]),
        ),
    ],
)
def test_get_links_from_tag(doc: str, root: str, expected: list[dict[str, str]]):
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(f".//{root}")
    assert el is not None

    links = html._get_links_from_tag(el)

    assert links == expected


# -- _is_text_tag() ------------------------------------------------------------------------------


def test_adjacent_spans_are_text_tags(opts_args: dict[str, Any]):
    html_str = "<div><span>&#8226;</span><span>A bullet!</span></div>"
    opts = HtmlPartitionerOptions(**opts_args)
    html_document = HTMLDocument(html_str, opts)
    el = html_document._main.find(".//div")
    assert el is not None

    assert html_document._is_text_tag(el) is True


# -- unit-level tests ----------------------------------------------------------------------------


class DescribeHTMLDocument:
    """Unit-test suite for `unstructured.documents.html.HTMLDocument`."""

    # -- ._main ----------------------------------

    def it_can_find_the_main_element_in_the_document(self, opts_args: dict[str, Any]):
        opts_args["text"] = (
            "<header></header>\n"
            "<body>\n"
            "  <p>Lots preamble stuff yada yada yada</p>\n"
            "  <main>\n"
            "    <article>\n"
            "      <section>\n"
            "        <h2>A Wonderful Section!</h2>\n"
            "        <p>Look at this amazing section!</p>\n"
            "      </section>\n"
            "      <section>\n"
            "        <h2>Another Wonderful Section!</h2>\n"
            "        <p>Look at this other amazing section!</p>\n"
            "      </section>\n"
            "    </article>\n"
            "  </main>\n"
            "</body>\n"
        )
        opts = HtmlPartitionerOptions(**opts_args)
        html_document = HTMLDocument.load(opts)
        assert html_document._main.tag == "main"

    def but_it_returns_the_root_when_no_main_element_is_present(self, opts_args: dict[str, Any]):
        opts_args["text"] = (
            "<header></header>\n"
            "<body>\n"
            "  <p>Lots preamble stuff yada yada yada</p>\n"
            "  <article>\n"
            "    <section>\n"
            "      <h2>A Wonderful Section!</h2>\n"
            "      <p>Look at this amazing section!</p>\n"
            "    </section>\n"
            "    <section>\n"
            "      <h2>Another Wonderful Section!</h2>\n"
            "      <p>Look at this other amazing section!</p>\n"
            "    </section>\n"
            "  </article>\n"
            "</body>\n"
        )
        opts = HtmlPartitionerOptions(**opts_args)
        html_document = HTMLDocument.load(opts)
        assert html_document._main.tag == "html"

    # -- ._parse_bulleted_text_from_table() ------

    def it_extracts_bullet_text_from_table_as_ListItem_elements(self, opts_args: dict[str, Any]):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = """
        <html>
          <body>
            <table>
              <tbody>
                <tr>
                  <td>•</td>
                  <td><p>Happy Groundhog's day!</p></td>
                </tr>
                <tr>
                  <td>•</td>
                  <td><p>Looks like six more weeks of winter ...</p></td>
                </tr>
              </tbody>
            </table>
          </body>
        </html>
        """
        html_document = HTMLDocument(html_str, opts)
        table_elem = html_document._main.find(".//table")
        assert table_elem is not None

        list_item_iter = html_document._parse_bulleted_text_from_table(table_elem)

        assert next(list_item_iter) == ListItem(text="Happy Groundhog's day!")
        assert next(list_item_iter) == ListItem(text="Looks like six more weeks of winter ...")
        with pytest.raises(StopIteration):
            next(list_item_iter)

    # -- ._parse_Table_from_table_elem() ---------

    def it_produces_one_cell_for_each_original_table_cell(self, opts_args: dict[str, Any]):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = (
            # -- include formatting whitespace to make sure it is removed --
            "<table>\n"
            "  <tr>\n"
            "    <td>foo</td>\n"
            "    <td>bar</td>\n"
            "  </tr>\n"
            "</table>"
        )
        html_document = HTMLDocument(html_str, opts)
        table_elem = html_document._main.find(".//table")
        assert table_elem is not None

        html_table = html_document._parse_Table_from_table_elem(table_elem)

        assert isinstance(html_table, Table)
        assert html_table.text == "foo bar"
        assert html_table.metadata.text_as_html == (
            "<table><tr><td>foo</td><td>bar</td></tr></table>"
        )

    # -- ._parse_tag() ---------------------------

    def it_produces_a_Text_element_when_the_tag_contents_are_not_narrative_or_a_title(
        self,
        is_possible_title_: Mock,
        opts_args: dict[str, Any],
    ):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = "<p>NO PARTICULAR TYPE.</p>"
        is_possible_title_.return_value = False
        html_document = HTMLDocument(html_str, opts)
        p = html_document._main.find(".//p")
        assert p is not None

        assert html_document._parse_tag(p) == Text(text="NO PARTICULAR TYPE.")

    def it_produces_a_ListItem_element_when_the_tag_contains_are_preceded_by_a_bullet_character(
        self, opts_args: dict[str, Any]
    ):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = "<p>● An excellent point!</p>"
        html_document = HTMLDocument(html_str, opts)
        p = html_document._main.find(".//p")
        assert p is not None

        assert html_document._parse_tag(p) == ListItem("An excellent point!")

    def but_not_when_the_tag_contains_only_a_bullet_character_and_no_text(
        self, opts_args: dict[str, Any]
    ):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = "<p>●</p>"
        html_document = HTMLDocument(html_str, opts)
        p = html_document._main.find(".//p")
        assert p is not None

        assert html_document._parse_tag(p) is None

    def it_returns_None_when_the_tag_has_no_content(self, opts_args: dict[str, Any]):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = "<p></p>"
        html_document = HTMLDocument(html_str, opts)
        p = html_document._main.find(".//p")
        assert p is not None

        assert html_document._parse_tag(p) is None

    def and_it_returns_None_when_the_tag_contains_only_a_stub(self, opts_args: dict[str, Any]):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = "<p>$</p>"
        html_document = HTMLDocument(html_str, opts)
        p = html_document._main.find(".//p")
        assert p is not None

        assert html_document._parse_tag(p) is None

    # -- ._process_list_item() -------------------------------------------------------------------

    def it_continues_processing_elements_after_a_bulleted_list(self, opts_args: dict[str, Any]):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = """
        <div>
            <p>●</p>
            <p>●</p>
        </div>
        <div>
            <p>An excellent point!</p>
        </div>
        """
        html_document = HTMLDocument(html_str, opts)
        el = html_document._main.find(".//div")
        assert el is not None

        parsed_el, _ = html_document._process_list_item(el, max_predecessor_len=10)

        assert parsed_el == ListItem(text="An excellent point!")

    def but_it_returns_None_when_no_element_follows_empty_bullets(self, opts_args: dict[str, Any]):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = """
        <div>
            <p>●</p>
            <p>●</p>
        </div>
        """
        html_document = HTMLDocument(html_str, opts)
        el = html_document._main.find(".//div")
        assert el is not None

        parsed_el, _ = html_document._process_list_item(el)

        assert parsed_el is None

    def and_it_returns_None_when_following_element_contains_no_text(
        self, opts_args: dict[str, Any]
    ):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = """
        <div>
            <p>●</p>
            <p>●</p>
        </div>
        <div>
        </div>
        """
        html_document = HTMLDocument(html_str, opts)
        el = html_document._main.find(".//div")
        assert el is not None

        parsed_el, _ = html_document._process_list_item(el)

        assert parsed_el is None

    def it_ignores_deep_divs_when_so_instructed(self, opts_args: dict[str, Any]):
        opts = HtmlPartitionerOptions(**opts_args)
        html_str = """
        <div>
            <p>●</p>
            <p>●</p>
            <p>●</p>
            <p>●</p>
            <p>●</p>
        </div>
        <div>
            <p>An excellent point!</p>
        </div>
        """
        html_document = HTMLDocument(html_str, opts)
        el = html_document._main.find(".//div")
        assert el is not None

        parsed_el, _ = html_document._process_list_item(el, max_predecessor_len=2)

        assert parsed_el is None


# -- module-level fixtures -----------------------------------------------------------------------


@pytest.fixture
def is_possible_narrative_text_(request: FixtureRequest):
    return function_mock(request, "unstructured.documents.html.is_possible_narrative_text")


@pytest.fixture
def is_possible_title_(request: FixtureRequest):
    return function_mock(request, "unstructured.documents.html.is_possible_title")


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
        "date_from_file_object": False,
        "metadata_last_modified": None,
        "skip_headers_and_footers": False,
        "detection_origin": None,
    }


@pytest.fixture
def pages_prop_(request: FixtureRequest):
    return property_mock(request, HTMLDocument, "pages")
