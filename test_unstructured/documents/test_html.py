# pyright: reportPrivateUsage=false

import os
import pathlib
from typing import Dict, List

import pytest
from lxml import etree
from lxml import html as lxml_html

from unstructured.documents import html
from unstructured.documents.base import Page
from unstructured.documents.elements import (
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
)
from unstructured.documents.html import (
    HEADING_TAGS,
    LIST_ITEM_TAGS,
    SECTION_TAGS,
    TABLE_TAGS,
    TEXT_TAGS,
    HTMLAddress,
    HTMLDocument,
    HTMLNarrativeText,
    HTMLTable,
    HTMLText,
    HTMLTitle,
    TagsMixin,
    _parse_HTMLTable_from_table_elem,
)

DIRECTORY = pathlib.Path(__file__).parent.resolve()

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

INCLUDED_TAGS = TEXT_TAGS + HEADING_TAGS + LIST_ITEM_TAGS + SECTION_TAGS
EXCLUDED_TAGS = [
    tag
    for tag in TAGS
    if tag not in (INCLUDED_TAGS + TABLE_TAGS + VOID_TAGS + ["html", "head", "body"])
]


# -- table-extraction behaviors ------------------------------------------------------------------


def test_it_can_parse_a_bare_bones_table_to_an_HTMLTable_element():
    """Bare-bones means no `<thead>`, `<tbody>`, or `<tfoot>` elements."""
    html_str = (
        "<html>\n"
        "<body>\n"
        "  <table>\n"
        "    <tr><td>Lorem</td><td>Ipsum</td></tr>\n"
        "    <tr><td>Ut enim non</td><td>ad minim\nveniam quis</td></tr>\n"
        "  </table>\n"
        "</body>\n"
        "</html>"
    )

    html_document = HTMLDocument.from_string(html_str)

    # -- there is exactly one element and it's an HTMLTable instance --
    (element,) = html_document.elements
    assert isinstance(element, HTMLTable)
    # -- table text is joined into a single string; no row or cell boundaries are represented --
    assert element.text == "Lorem Ipsum Ut enim non ad minim\nveniam quis"
    # -- An HTML representation is also available that is longer but represents table structure.
    # -- Note this is padded with undesired spaces for human-readability that doesn't matter to us.
    assert element.text_as_html == (
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
    html_str = (
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

    html_document = HTMLDocument.from_string(html_str)

    (element,) = html_document.elements
    assert isinstance(element, HTMLTable)
    assert element.text_as_html == (
        "<table>"
        "<tr><td>Lorem</td><td>Ipsum</td></tr>"
        "<tr><td>Lorem ipsum</td><td>dolor sit amet nulla</td></tr>"
        "<tr><td>Ut enim non</td><td>ad minim<br/>veniam quis</td></tr>"
        "<tr><td>Dolor</td><td>Equis</td></tr>"
        "</table>"
    )


def test_it_does_not_emit_an_HTMLTable_element_for_a_table_with_no_text():
    html_str = (
        "<html>\n"
        "<body>\n"
        "  <table>\n"
        "    <tr><td> </td><td> </td></tr>\n"
        "    <tr><td> </td><td> </td></tr>\n"
        "  </table>\n"
        "</body>\n"
        "</html>"
    )

    html_document = HTMLDocument.from_string(html_str)

    assert html_document.elements == []


def test_it_does_not_consider_an_empty_table_a_bulleted_text_table():
    html_str = (
        "<html>\n"
        "<body>\n"
        "  <table>\n"
        "    <tr><td> </td><td> </td></tr>\n"
        "    <tr><td> </td><td> </td></tr>\n"
        "  </table>\n"
        "</body>\n"
        "</html>"
    )
    html_document = HTMLDocument.from_string(html_str)
    html_elem = html_document.document_tree
    assert html_elem is not None
    table = html_elem.find(".//table")
    assert table is not None

    assert html._is_bulleted_table(table) is False


def test_it_provides_parseable_HTML_in_text_as_html():
    html_str = (
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
    html_document = HTMLDocument.from_string(html_str)
    (element,) = html_document.elements
    assert isinstance(element, HTMLTable)
    text_as_html = element.text_as_html
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


# -- element-suppression behaviors ---------------------------------------------------------------


def test_it_does_not_extract_text_in_script_tags():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "example-with-scripts.html")
    doc = HTMLDocument.from_file(filename=filename)
    assert all("function (" not in element.text for element in doc.elements)


def test_it_does_not_extract_text_in_style_tags():
    html_str = (
        "<html>\n"
        "<body>\n"
        "  <p><style> p { margin:0; padding:0; } </style>Lorem ipsum dolor</p>\n"
        "</body>\n"
        "</html>"
    )

    html_document = HTMLDocument.from_string(html_str)

    (element,) = html_document.elements
    assert isinstance(element, Text)
    assert element.text == "Lorem ipsum dolor"


# ------------------------------------------------------------------------------------------------


def test_parses_tags_correctly():
    raw_html = """<html>
    <body>
        <table>
            <tbody>
                <tr>
                    <td><p>Hi there!</p></td>
                </tr>
            </tbody>
        </table>
    </body>
</html>"""
    doc = HTMLDocument.from_string(raw_html)
    el = doc.elements[0]
    assert el.ancestortags + (el.tag,) == ("html", "body", "table")


def test_has_table_ancestor():
    title = HTMLTitle(
        "I am a Title",
        tag="td",
        ancestortags=["html", "body", "table", "tr"],
    )
    assert html.has_table_ancestor(title)


def test_has_no_table_ancestor():
    title = HTMLTitle(
        "I am a Title",
        tag="p",
        ancestortags=["html", "body"],
    )
    assert not html.has_table_ancestor(title)


def test_read_without_skipping_table(monkeypatch):
    monkeypatch.setattr(html, "is_possible_narrative_text", lambda *args: True)
    doc = """<html>
    <body>
        <table>
            <tbody>
                <tr>
                    <td><p>Hi there! I am Matt!</p></td>
                </tr>
            </tbody>
        </table>
    </body>
</html>"""
    document = HTMLDocument.from_string(doc).doc_after_cleaners(skip_table=False)
    assert document.pages[0].elements[0] == Table(text="Hi there! I am Matt!")


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
def test_construct_text(doc, expected):
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    para = document_tree.find(".//p")
    text = html._construct_text(para)
    assert text == expected


@pytest.mark.parametrize(
    ("doc", "root", "expected"),
    [
        (
            "<p>Hello <strong>there</strong> I <em>am</em> a <b>very</b> <i>important</i> text</p>",
            "p",
            [
                {"text": "there", "tag": "strong"},
                {"text": "am", "tag": "em"},
                {"text": "very", "tag": "b"},
                {"text": "important", "tag": "i"},
            ],
        ),
        (
            "<p>Here is a <span>list</span> of <b>my <i>favorite</i> things</b></p>",
            "p",
            [
                {"text": "list", "tag": "span"},
                {"text": "my favorite things", "tag": "b"},
                {"text": "favorite", "tag": "i"},
            ],
        ),
        (
            "<strong>A lone strong text!</strong>",
            "strong",
            [{"text": "A lone strong text!", "tag": "strong"}],
        ),
        ("<span>I have a</span> tail", "span", [{"text": "I have a", "tag": "span"}]),
        ("<p>Text with no emphasized runs</p> ", "p", []),
    ],
)
def test_get_emphasized_texts_from_tag(doc: str, root: str, expected: List[Dict[str, str]]):
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(f".//{root}")
    assert el is not None

    emphasized_texts = html._get_emphasized_texts_from_tag(el)

    assert emphasized_texts == expected


@pytest.mark.parametrize(
    ("doc", "root", "expected"),
    [
        (
            "<a href='/loner'>A lone link!</a>",
            "a",
            [{"text": "A lone link!", "url": "/loner", "start_index": -1}],
        ),
        (
            "<ul><li><a href='/wiki/Parrot'>Parrots</a></li><li>Dogs</li></ul>",
            "ul",
            [{"text": "Parrots", "url": "/wiki/Parrot", "start_index": 0}],
        ),
        (
            "<ul><li><a href='/parrot'>Parrots</a></li><li><a href='/dog'>Dogs</a></li></ul>",
            "ul",
            [
                {"text": "Parrots", "url": "/parrot", "start_index": 0},
                {"text": "Dogs", "url": "/dog", "start_index": 7},
            ],
        ),
        (
            "<div>Here is <p>P tag</p> tail text. <a href='/link'>link!</a></div>",
            "div",
            [{"text": "link!", "url": "/link", "start_index": 25}],
        ),
        (
            "<div>Here is <p>P tag</p><a href='/link'>link!</a></div>",
            "div",
            [{"text": "link!", "url": "/link", "start_index": 13}],
        ),
    ],
)
def test_get_links_from_tag(doc: str, root: str, expected: List[Dict[str, str]]):
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(f".//{root}")
    assert el is not None

    links = html._get_links_from_tag(el)

    assert links == expected


def test_parse_nothing():
    doc = """<p></p>"""
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//p")
    parsed_el = html._parse_tag(el)
    assert parsed_el is None


def test_read_with_existing_pages():
    page = Page(number=0)
    html_document = HTMLDocument.from_pages([page])
    assert html_document.pages == [page]


def test_parse_not_anything(monkeypatch):
    monkeypatch.setattr(html, "is_narrative_tag", lambda *args: False)
    monkeypatch.setattr(html, "is_possible_title", lambda *args: False)
    doc = """<p>This is nothing</p>"""
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//p")
    parsed_el = html._parse_tag(el)
    assert parsed_el == Text(text="This is nothing")


def test_parse_bullets(monkeypatch):
    doc = """<p>● An excellent point!</p>"""
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//p")
    parsed_el = html._parse_tag(el)
    assert parsed_el == ListItem("An excellent point!")


def test_parse_tag_ignores_lonely_bullets():
    doc = """<p>●</p>"""
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//p")
    parsed_el = html._parse_tag(el)
    assert parsed_el is None


def test_parse_tag_ignores_stubs():
    doc = """<p>$</p>"""
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//p")
    parsed_el = html._parse_tag(el)
    assert parsed_el is None


def test_adjacent_spans_are_text_tags():
    doc = """<div><span>&#8226;</span><span>A bullet!</span></div>"""
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//div")
    assert html._is_text_tag(el) is True


def test_process_list_item_gets_next_section():
    doc = """
    <div>
        <p>●</p>
        <p>●</p>
    </div>
    <div>
        <p>An excellent point!</p>
    </div>

    """
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//div")
    parsed_el, _ = html._process_list_item(el, max_predecessor_len=10)
    assert parsed_el == ListItem(text="An excellent point!")


def test_get_bullet_descendants():
    div_1 = "<div><p>●</p><p>●</p></div>"
    document_tree_1 = etree.fromstring(div_1, etree.HTMLParser())
    element = document_tree_1.find(".//div")

    div_2 = "<div><p>An excellent point!</p></div>"
    document_tree_2 = etree.fromstring(div_2, etree.HTMLParser())
    next_element = document_tree_2.find(".//div")

    descendants = html._get_bullet_descendants(element, next_element)
    assert len(descendants) == 1


def test_process_list_item_returns_none_if_next_blank():
    doc = """
    <div>
        <p>●</p>
        <p>●</p>
    </div>

    """
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//div")
    parsed_el, _ = html._process_list_item(el)
    assert parsed_el is None


def test_process_list_item_returns_none_if_next_has_no_text():
    doc = """
    <div>
        <p>●</p>
        <p>●</p>
    </div>
    <div>
    </div>
    """
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//div")
    assert html.is_list_item_tag(el) is True
    parsed_el, _ = html._process_list_item(el)
    assert parsed_el is None


def test_process_list_item_ignores_deep_divs():
    doc = """
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
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    el = document_tree.find(".//div")
    parsed_el, _ = html._process_list_item(el, max_predecessor_len=2)
    assert parsed_el is None


def test_read_html_doc(tmpdir, monkeypatch):
    TITLE1 = "A Great and Glorious Section"
    SECTION1 = "Dear Leader is the best. He is such a wonderful engineer!"
    TITLE2 = "Another Magnificent Title"
    SECTION2 = "The last section is a title because of its capitalization patterns!"
    TABLE_SECTION = "Skip me because I'm in a table"
    TITLE3 = "A New Beginning"
    SECTION3 = "Here is the start of a new page."

    doc = f"""<html>
    <body>
        <header>
            <p>Here is a header. We want to ignore anything that is in this section.</p>
        </header>
        <h1>{TITLE1}</h1>
        <p>{SECTION1}</p>
        <p></p>
        <p>{TITLE2}</p>
        <p><b>{SECTION2}</b></p>
        <table>
            <tbody>
                <tr>
                    <td><p>{TABLE_SECTION}</p></td>
                </tr>
            </tbody>
        </table>
        <hr>
        <h2>{TITLE3}</h2>
        <div>{SECTION3}</div>
        <footer>
            <p>Here is a footer. We want to ignore anything that is in this section</p>
        </footer>
        <div>
            <p>Let's ignore anything after the footer too since it's probably garbage.</p>
        </div>
    </body>
</html>"""
    filename = os.path.join(tmpdir.dirname, "sample-doc.html")
    with open(filename, "w") as f:
        f.write(doc)

    html_document = HTMLDocument.from_file(filename=filename).doc_after_cleaners(
        skip_headers_and_footers=True,
        skip_table=True,
    )
    print("original pages: ", HTMLDocument.from_file(filename=filename).pages)
    print("filtered pages: ", html_document.pages)
    print([el.text for el in html_document.pages[0].elements])

    assert len(html_document.pages) == 2

    page_one = html_document.pages[0]
    assert len(page_one.elements) == 4
    assert page_one.elements == [
        Title(text=TITLE1),
        NarrativeText(text=SECTION1),
        Title(text=TITLE2),
        NarrativeText(text=SECTION2),
    ]

    page_two = html_document.pages[1]
    assert len(page_two.elements) == 2
    assert page_two.elements == [
        Title(text=TITLE3),
        NarrativeText(text=SECTION3),
    ]

    pages = html_document.pages
    assert all(isinstance(page, Page) for page in pages)


def test_find_main():
    html_str = """<header></header>
    <body>
        <p>Lots preamble stuff yada yada yada</p>
        <main>
            <article>
                <section>
                    <h2>A Wonderful Section!</h2>
                    <p>Look at this amazing section!</p>
                </section>
                <section>
                    <h2>Another Wonderful Section!</h2>
                    <p>Look at this other amazing section!</p>
                </section>
            </article>
        </main>
    </body>"""
    html_document = HTMLDocument.from_string(html_str)
    document_tree = html_document.document_tree
    main_tag = html._find_main(document_tree)
    assert main_tag.tag == "main"


def test_find_main_returns_doc_when_main_not_present():
    html_str = """<header></header>
    <body>
    <p>Lots preamble stuff yada yada yada</p>
        <article>
            <section>
                <h2>A Wonderful Section!</h2>
                <p>Look at this amazing section!</p>
            </section>
            <section>
                <h2>Another Wonderful Section!</h2>
                <p>Look at this other amazing section!</p>
            </section>
        </article>
    </body>"""
    html_document = HTMLDocument.from_string(html_str)
    document_tree = html_document.document_tree
    root = html._find_main(document_tree)
    assert root.tag == "html"


def test_find_articles():
    html_str = """<header></header>
    <body>
    <p>Lots preamble stuff yada yada yada</p>
        <article>
            <h2>A Wonderful Section!</h2>
            <p>Look at this amazing section!</p>
        </article>
        <article>
            <h2>Another Wonderful Section!</h2>
            <p>Look at this other amazing section!</p>
        </article>
    </body>"""
    html_document = HTMLDocument.from_string(html_str)
    document_tree = html_document.document_tree
    articles = html._find_articles(document_tree)
    assert len(articles) == 2


def test_find_articles_returns_doc_when_none_present():
    html_str = """<header></header>
    <body>
    <p>Lots preamble stuff yada yada yada</p>
        <section>
            <h2>A Wonderful Section!</h2>
            <p>Look at this amazing section!</p>
        </section>
        <section>
            <h2>Another Wonderful Section!</h2>
            <p>Look at this other amazing section!</p>
        </section>
    </body>"""
    html_document = HTMLDocument.from_string(html_str)
    document_tree = html_document.document_tree
    articles = html._find_articles(document_tree)
    assert len(articles) == 1


def test_include_headers_and_footers(sample_doc):
    html_document = sample_doc.doc_after_cleaners(skip_headers_and_footers=False)
    assert len(html_document.pages[1].elements) == 3


def test_include_table_text(sample_doc):
    html_document = sample_doc.doc_after_cleaners(skip_table=False)
    assert len(html_document.pages[0].elements) == 2


@pytest.mark.parametrize("tag", [tag for tag in TEXT_TAGS if tag not in TABLE_TAGS])
def test_tag_types(tag):
    html_str = f"""
    <body>
        <{tag}>
            There is some text here.
        </{tag}>
    </body>
    """
    html_document = HTMLDocument.from_string(html_str)
    assert len(html_document.pages[0].elements) == 1


@pytest.mark.parametrize("tag", EXCLUDED_TAGS)
def test_exclude_tag_types(tag):
    html_str = f"""
    <body>
        <{tag}>
            There is some text here.
        </{tag}>
    </body>
    """
    html_document = HTMLDocument.from_string(html_str)
    assert len(html_document.pages) == 0


def test_tag_types_table(sample_doc):
    html_document = sample_doc.doc_after_cleaners(skip_table=True)
    assert len(html_document.pages[0].elements) == 2


def test_nested_text_tags():
    tag1, tag2 = [tag for tag in TEXT_TAGS if tag not in TABLE_TAGS][:2]
    html_str = f"""
    <body>
        <{tag1}>
            <{tag2}>
                There is some text here.
            </{tag2}>
        </{tag1}>
    </body>
    """
    html_document = HTMLDocument.from_string(html_str).doc_after_cleaners(skip_table=False)
    assert len(html_document.pages[0].elements) == 1


def test_containers_with_text_are_processed():
    html_str = """<div dir=3D"ltr">Hi All,<div><br></div>
   <div>Get excited for our first annual family day!</div>
   <div>Best.<br clear=3D"all">
      <div><br></div>
      -- <br>
      <div dir=3D"ltr">
         <div dir=3D"ltr">Dino the Datasaur<div>Unstructured Technologies<br><div>Data Scientist
                </div>
                <div>Doylestown, PA 18901</div>
               <div><br></div>
            </div>
         </div>
      </div>
   </div>
</div>"""
    html_document = HTMLDocument.from_string(html_str)

    assert html_document.elements == [
        HTMLText(text="Hi All,", tag="div"),
        HTMLNarrativeText(text="Get excited for our first annual family day!", tag="div"),
        HTMLTitle(text="Best.", tag="div"),
        HTMLText(text="\n      -- ", tag="div"),
        HTMLTitle(text="Dino the Datasaur", tag="div"),
        HTMLTitle(text="Unstructured Technologies", tag="div"),
        HTMLTitle(text="Data Scientist", tag="div"),
        HTMLAddress(text="Doylestown, PA 18901", tag="div"),
    ]


def test_html_grabs_bulleted_text_in_tags():
    html_str = """<html>
    <body>
        <ol>
            <li>Happy Groundhog's day!</li>
            <li>Looks like six more weeks of winter ...</li>
        </ol>
    </body>
</html>"""
    html_document = HTMLDocument.from_string(html_str)

    assert html_document.elements == [
        ListItem(text="Happy Groundhog's day!"),
        ListItem(text="Looks like six more weeks of winter ..."),
    ]


def test_html_grabs_bulleted_text_in_paras():
    html_str = """<html>
    <body>
        <p>
            <span>&#8226; Happy Groundhog's day!</span>
        </p>
        <p>
            <span>&#8226; Looks like six more weeks of winter ...</span>
        </p>
    </body>
</html>"""
    html_document = HTMLDocument.from_string(html_str)

    assert html_document.elements == [
        ListItem(text="Happy Groundhog's day!"),
        ListItem(text="Looks like six more weeks of winter ..."),
    ]


def test_bulletized_bulleted_text_from_table():
    doc = """<html>
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
</html>"""
    document_tree = etree.fromstring(doc, etree.HTMLParser())
    table = document_tree.find(".//table")
    bulleted_text = html._bulleted_text_from_table(table)
    assert bulleted_text == [
        ListItem(text="Happy Groundhog's day!"),
        ListItem(text="Looks like six more weeks of winter ..."),
    ]


def test_html_grabs_bulleted_text_in_tables():
    html_str = """<html>
    <body>
        <table>
            <tbody>
                <tr>
                    <td>&#8226;</td>
                    <td><p>Happy Groundhog's day!</p></td>
                </tr>
                <tr>
                    <td>&#8226;</td>
                    <td><p>Looks like six more weeks of winter ...</p></td>
                </tr>
            </tbody>
        </table>
    </body>
</html>"""
    html_document = HTMLDocument.from_string(html_str)

    assert html_document.elements == [
        ListItem(text="Happy Groundhog's day!"),
        ListItem(text="Looks like six more weeks of winter ..."),
    ]


def test_raises_error_no_tag():
    with pytest.raises(TypeError):
        TagsMixin(tag=None)
    with pytest.raises(TypeError):
        TagsMixin()


def test_raises_error_wrong_elements(monkeypatch, sample_doc):
    page = Page(0)
    page.elements = ["this should def not be a string"]
    monkeypatch.setattr(sample_doc, "_pages", [page])
    with pytest.raises(ValueError):
        sample_doc.doc_after_cleaners()


def test_filter_in_place():
    html_doc = """
    <table><tbody><tr><td>A table thing.</td></tr></tbody></table>
    <p>A non-table thing</p>
    """
    doc = HTMLDocument.from_string(html_doc)
    assert len(doc.elements) == 2
    doc.doc_after_cleaners(skip_table=True, inplace=True)
    assert len(doc.elements) == 1


def test_joins_tag_text_correctly():
    raw_html = "<p>Hello again peet mag<i>ic</i>al</p>"
    doc = HTMLDocument.from_string(raw_html)
    el = doc.elements[0]
    assert el.text == "Hello again peet magical"


def test_sample_doc_with_emoji():
    raw_html = """
    <html charset="unicode">
        <p>Hello again 😀</p>
    </html>
    """
    doc = HTMLDocument.from_string(raw_html)
    # NOTE(robinson) - unclear why right now, but the output is the emoji on the test runners
    # and the byte string representation when running locally on mac
    assert doc.elements[0].text in ["Hello again ð\x9f\x98\x80", "Hello again 😀"]


def test_only_plain_text_in_body():
    raw_html = "<body>Hello</body>"
    doc = HTMLDocument.from_string(raw_html)
    assert doc.elements[0].text == "Hello"


def test_plain_text_before_anything_in_body():
    raw_html = "<body>Hello<p>World</p></body>"
    doc = HTMLDocument.from_string(raw_html)
    assert doc.elements[0].text == "Hello"
    assert doc.elements[1].text == "World"


def test_line_break_in_container():
    raw_html = "<div>Hello<br/>World</div>"
    doc = HTMLDocument.from_string(raw_html)
    assert doc.elements[0].text == "Hello"
    assert doc.elements[1].text == "World"


@pytest.mark.parametrize("tag", TEXT_TAGS)
def test_line_break_in_text_tag(tag):
    raw_html = f"<{tag}>Hello<br/>World</{tag}>"
    doc = HTMLDocument.from_string(raw_html)
    assert doc.elements[0].text == "Hello"
    assert doc.elements[1].text == "World"


# -- unit-level tests ----------------------------------------------------------------------------


class Describe_parse_HTMLTable_from_table_elem:
    """Unit-test suite for `unstructured.documents.html._parse_HTMLTable_from_table_elem`."""

    def it_produces_one_cell_for_each_original_table_cell(self):
        table_html = (
            # -- include formatting whitespace to make sure it is removed --
            "<table>\n"
            "  <tr>\n"
            "    <td>foo</td>\n"
            "    <td>bar</td>\n"
            "  </tr>\n"
            "</table>"
        )
        table_elem = lxml_html.fromstring(table_html)  # pyright: ignore[reportUnknownMemberType]

        html_table = _parse_HTMLTable_from_table_elem(table_elem)

        assert isinstance(html_table, HTMLTable)
        assert html_table.text == "foo bar"
        assert html_table.text_as_html == "<table><tr><td>foo</td><td>bar</td></tr></table>"

    def it_accommodates_tds_with_child_elements(self):
        """Like this example from an SEC 10k filing."""
        table_html = (
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
        table_elem = lxml_html.fromstring(table_html)  # pyright: ignore[reportUnknownMemberType]

        html_table = _parse_HTMLTable_from_table_elem(table_elem)

        assert isinstance(html_table, HTMLTable)
        assert html_table.text == (
            "☒ ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934"
        )
        print(f"{html_table.text_as_html=}")
        assert html_table.text_as_html == (
            "<table>"
            "<tr><td></td><td></td></tr>"
            "<tr><td>☒</td><td>ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES"
            " EXCHANGE ACT OF 1934</td></tr>"
            "</table>"
        )

    def it_reduces_a_nested_table_to_its_text_placed_in_the_cell_containing_the_nested_table(self):
        """Recursively ..."""
        nested_table_html = (
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
        table_elem = lxml_html.fromstring(  # pyright: ignore[reportUnknownMemberType]
            nested_table_html
        )

        html_table = _parse_HTMLTable_from_table_elem(table_elem)

        assert isinstance(html_table, HTMLTable)
        assert html_table.text == "foo bar baz bng fizz bang"
        assert html_table.text_as_html == (
            "<table><tr><td>foo bar baz bng</td><td>fizz bang</td></tr></table>"
        )


# -- module-level fixtures -----------------------------------------------------------------------


@pytest.fixture()
def sample_doc():
    table_element = HTMLTitle(
        "I'm a title in a table.",
        tag="p",
        ancestortags=("table", "tbody", "tr", "td"),
    )
    narrative = HTMLNarrativeText("I'm some narrative text", tag="p", ancestortags=())
    page1 = Page(0)
    page1.elements = [table_element, narrative]
    header = HTMLTitle("I'm a header", tag="header", ancestortags=())
    body = HTMLNarrativeText("Body text", tag="p", ancestortags=())
    footer = HTMLTitle("I'm a footer", tag="footer", ancestortags=())
    page2 = Page(1)
    page2.elements = [header, body, footer]
    doc = HTMLDocument.from_pages([page1, page2])
    return doc
