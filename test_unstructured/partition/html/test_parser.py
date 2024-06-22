# pyright: reportPrivateUsage=false
# pyright: reportUnknownArgumentType=false

"""Test suite for `unstructured.partition.html.parser` module."""

from __future__ import annotations

from collections import deque

import pytest
from lxml import etree

from unstructured.documents.elements import Address, Element, ListItem, NarrativeText, Text, Title
from unstructured.partition.html.parser import (
    Anchor,
    Annotation,
    DefaultElement,
    Flow,
    Phrasing,
    RemovedPhrasing,
    TextSegment,
    _consolidate_annotations,
    _normalize_text,
    html_parser,
)

# -- MODULE-LEVEL FUNCTIONS ----------------------------------------------------------------------

# -- _consolidate_annotations() ------------------


def it_gathers_annotations_from_text_segments():
    text_segments = [
        TextSegment(
            " Ford Prefect ",
            {
                "link_texts": "Ford Prefect",
                "link_url": "https://wikipedia/Ford_Prefect",
                "emphasized_text_contents": "Ford Prefect",
                "emphasized_text_tags": "b",
            },
        ),
        TextSegment(
            " alien  encounter",
            {
                "emphasized_text_contents": "alien encounter",
                "emphasized_text_tags": "bi",
            },
        ),
    ]

    annotations = _consolidate_annotations(text_segments)

    assert annotations == {
        # -- each distinct key gets a list of values --
        "emphasized_text_contents": ["Ford Prefect", "alien encounter"],
        "emphasized_text_tags": ["b", "bi"],
        # -- even when there is only one value --
        "link_texts": ["Ford Prefect"],
        "link_url": ["https://wikipedia/Ford_Prefect"],
    }
    # -- and the annotations mapping is immutable --
    with pytest.raises(TypeError, match="object does not support item assignment"):
        annotations["new_key"] = "foobar"  # pyright: ignore[reportIndexIssue]
    # -- (but not its list values unfortunately) --
    annotations["emphasized_text_tags"].append("xyz")
    assert annotations["emphasized_text_tags"] == ["b", "bi", "xyz"]


# -- _normalize_text() ---------------------------


@pytest.mark.parametrize(
    ("text", "expected_value"),
    [
        # -- already normalized text is left unchanged --
        ("iterators allow", "iterators allow"),
        # -- newlines are treated as whitespace --
        ("algorithm\nto   be", "algorithm to be"),
        ("  separated\n  from  ", "separated from"),
        ("\n container\n details\n ", "container details"),
        (
            "\n  iterators  allow \n algorithm to be   \nexpressed  without container  \nnoise",
            "iterators allow algorithm to be expressed without container noise",
        ),
    ],
)
def test_normalize_text_produces_normalized_text(text: str, expected_value: str):
    assert _normalize_text(text) == expected_value


# -- FLOW (BLOCK-ITEM) ELEMENTS ------------------------------------------------------------------


class DescribeFlow:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Flow`.

    The `Flow` class provides most behaviors for flow (block-level) elements.
    """

    # -- .is_phrasing -----------------------------------------------------

    def it_knows_it_is_NOT_a_phrasing_element(self):
        p = etree.fromstring("<p>Hello</p>", html_parser).xpath(".//p")[0]

        assert isinstance(p, Flow)
        assert p.is_phrasing is False

    # -- .iter_elements() -------------------------------------------------

    def it_generates_the_document_elements_from_the_Flow_element(self):
        """Phrasing siblings of child block elements are processed with text or tail.

        In the general case, a Flow element can contain text, phrasing content, and child flow
        elements.

        Each of these five lines in this example is a "paragraph" and gives rise to a distinct
        document-element.
        """
        html_text = """
          <div>
            Text of div <b>with <i>hierarchical</i>\nphrasing</b> content before first block item
            <p>Click <a href="http://blurb.io">here</a> to see the blurb for this block item. </p>
            tail of block item <b>with <i>hierarchical</i> phrasing </b> content
            <p>second block item</p>
            tail of block item <b>with <i>  hierarchical  </i></b> phrasing content
          </div>
        """
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div.iter_elements()

        e = next(elements)
        assert e == Title("Text of div with hierarchical phrasing content before first block item")
        assert e.metadata.to_dict() == {
            "category_depth": 0,
            "emphasized_text_contents": ["with", "hierarchical", "phrasing"],
            "emphasized_text_tags": ["b", "bi", "b"],
        }
        e = next(elements)
        assert e == NarrativeText("Click here to see the blurb for this block item.")
        assert e.metadata.to_dict() == {"link_texts": ["here"], "link_urls": ["http://blurb.io"]}
        e = next(elements)
        assert e == Title("tail of block item with hierarchical phrasing content")
        assert e.metadata.to_dict() == {
            "category_depth": 0,
            "emphasized_text_contents": ["with", "hierarchical", "phrasing"],
            "emphasized_text_tags": ["b", "bi", "b"],
        }
        e = next(elements)
        assert e == Title("second block item")
        assert e.metadata.to_dict() == {"category_depth": 0}
        e = next(elements)
        assert e == Title("tail of block item with hierarchical phrasing content")
        assert e.metadata.to_dict() == {
            "category_depth": 0,
            "emphasized_text_contents": ["with", "hierarchical"],
            "emphasized_text_tags": ["b", "bi"],
        }
        with pytest.raises(StopIteration):
            e = next(elements)

    # -- ._category_depth() -----------------------------------------------

    @pytest.mark.parametrize(
        ("html_text", "tag", "ElementCls", "expected_value"),
        [
            ("<p>Ford... you're turning into a penguin. Stop it.<p>", "p", Text, None),
            ("<p>* thanks for all the fish.</p>", "p", ListItem, 0),
            ("<li>thanks for all the fish.</li>", "li", ListItem, 0),
            ("<ul><li>So long</li><li>and thanks for all the fish.</li></ul>", "li", ListItem, 1),
            ("<dl><dd>So long<ol><li>and thanks for the fish.</li></ol></ul>", "li", ListItem, 2),
            ("<p>Examples</p>", "p", Title, 0),
            ("<h1>Examples</h1>", "h1", Title, 0),
            ("<h2>Examples</h2>", "h2", Title, 1),
            ("<h3>Examples</h3>", "h3", Title, 2),
            ("<h4>Examples</h4>", "h4", Title, 3),
            ("<h5>Examples</h5>", "h5", Title, 4),
            ("<h6>Examples</h6>", "h6", Title, 5),
        ],
    )
    def it_computes_the_category_depth_to_help(
        self, html_text: str, tag: str, ElementCls: type[Element], expected_value: int | None
    ):
        e = etree.fromstring(html_text, html_parser).xpath(f".//{tag}")[0]
        assert e._category_depth(ElementCls) == expected_value

    # -- ._element_from_text_or_tail() ------------------------------------

    def it_assembles_text_and_tail_document_elements_to_help(self):
        """Text and tails and their phrasing content are both processed the same way."""
        html_text = "<div>The \n Roman <b>poet <i>   Virgil</i> gave</b> his <q>pet</q> fly</div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div), Text)

        e = next(elements)
        # -- element text is normalized --
        assert e == Text("The Roman poet Virgil gave his pet fly")
        # -- individual annotations are consolidated --
        assert e.metadata.to_dict() == {
            "emphasized_text_contents": ["poet", "Virgil", "gave"],
            "emphasized_text_tags": ["b", "bi", "b"],
        }

    def but_it_does_not_generate_a_document_element_when_only_whitespace_is_contained(self):
        html_text = "<div>   <b> \n <i>  \n </i>  </b>   <q> \n </q> \n  </div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div), Text)

        with pytest.raises(StopIteration):
            next(elements)

    def it_uses_the_specified_element_class_to_form_the_document_element(self):
        html_text = "<div>\n  The line-storm clouds fly tattered and swift\n</div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div), Address)

        e = next(elements)
        assert e == Address("The line-storm clouds fly tattered and swift")
        assert e.metadata.to_dict() == {}
        with pytest.raises(StopIteration):
            next(elements)

    def and_it_selects_the_document_element_class_by_analyzing_the_text_when_not_specified(self):
        html_text = "<div>\n  The line-storm clouds fly tattered and swift,\n</div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div))

        assert next(elements) == NarrativeText("The line-storm clouds fly tattered and swift,")

    def but_it_does_not_generate_a_document_element_when_only_a_bullet_character_is_contained(self):
        html_text = "<div> * </div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div))

        with pytest.raises(StopIteration):
            next(elements)

    # -- ._iter_text_segments() -------------------------------------------

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            (  # -- text with no phrasing --
                "<p>Ford... you're turning into a penguin.<p>",
                [("Ford... you're turning into a penguin.", {})],
            ),
            (  # -- text with phrasing --
                "<p>Ford... <b>you're turning</b> into\na <i>penguin</i>.<p>",
                [
                    ("Ford... ", {}),
                    (
                        "you're turning",
                        {"emphasized_text_contents": "you're turning", "emphasized_text_tags": "b"},
                    ),
                    (" into\na ", {}),
                    (
                        "penguin",
                        {"emphasized_text_contents": "penguin", "emphasized_text_tags": "i"},
                    ),
                    (".", {}),
                ],
            ),
            (  # -- text with nested phrasing --
                "<p>Ford... <b>you're <i>turning</i></b> into a penguin.<p>",
                [
                    ("Ford... ", {}),
                    (
                        "you're ",
                        {"emphasized_text_contents": "you're", "emphasized_text_tags": "b"},
                    ),
                    (
                        "turning",
                        {"emphasized_text_contents": "turning", "emphasized_text_tags": "bi"},
                    ),
                    (" into a penguin.", {}),
                ],
            ),
        ],
    )
    def it_recursively_generates_text_segments_from_text_and_phrasing_to_help(
        self, html_text: str, expected_value: list[Annotation]
    ):
        p = etree.fromstring(html_text, html_parser).xpath(".//p")[0]
        text_segments = list(p._iter_text_segments(p.text, deque(p)))

        assert text_segments == expected_value


class DescribePre:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Pre`.

    The `Pre` class specializes behaviors for the `<pre>` (pre-formatted text) element.
    """

    def it_preserves_the_whitespace_of_its_phrasing_only_contents(self):
        """A `<pre>` element can contain only phrasing content."""
        html_text = (
            "<pre>\n"
            "  The Answer to the Great Question...   Of Life, the Universe and Everything...\n"
            "  Is... Forty-two, said Deep Thought, with infinite majesty and calm.\n"
            "</pre>\n"
        )
        pre = etree.fromstring(html_text, html_parser).xpath(".//pre")[0]

        elements = pre.iter_elements()

        e = next(elements)
        assert e == Text(
            "  The Answer to the Great Question...   Of Life, the Universe and Everything...\n"
            "  Is... Forty-two, said Deep Thought, with infinite majesty and calm."
        )
        with pytest.raises(StopIteration):
            next(elements)

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            # -- a newline in the 0th position of pre.text is dropped --
            ("<pre>\n  foo  </pre>", "  foo  "),
            # -- but not when preceded by any other whitespace --
            ("<pre> \n  foo  </pre>", " \n  foo  "),
            # -- and only one is dropped --
            ("<pre>\n\n  foo  </pre>", "\n  foo  "),
            # -- a newline in the -1th position is dropped --
            ("<pre>  foo  \n</pre>", "  foo  "),
            # -- but not when followed by any other whitespace --
            ("<pre>  foo  \n </pre>", "  foo  \n "),
            # -- and only one is dropped --
            ("<pre>  foo  \n\n</pre>", "  foo  \n"),
            # -- a newline in both positions are both dropped --
            ("<pre>\n  foo  \n</pre>", "  foo  "),
            # -- or not when not at the absolute edge --
            ("<pre> \n  foo  \n </pre>", " \n  foo  \n "),
        ],
    )
    def but_it_strips_a_single_leading_or_trailing_newline(
        self, html_text: str, expected_value: str
    ):
        """Content starts on next line when opening `<pre>` tag is immediately followed by `\n`"""
        pre = etree.fromstring(html_text, html_parser).xpath(".//pre")[0]
        e = next(pre.iter_elements())

        assert e.text == expected_value

    def it_assigns_emphasis_and_link_metadata_when_contents_have_those_phrasing_elements(self):
        html_text = '<pre>You\'re <b>turning</b> into a <a href="http://eie.io">penguin</a>.</pre>'
        pre = etree.fromstring(html_text, html_parser).xpath(".//pre")[0]

        e = next(pre.iter_elements())

        assert e.text == "You're turning into a penguin."
        assert e.metadata.emphasized_text_contents == ["turning"]
        assert e.metadata.emphasized_text_tags == ["b"]
        assert e.metadata.link_texts == ["penguin"]
        assert e.metadata.link_urls == ["http://eie.io"]


class DescribeRemovedBlock:
    """Isolated unit-test suite for `unstructured.partition.html.parser.RemovedBlock`.

    This class is used for block level items we want to skip like `<hr/>` and `<figure>`.
    """

    def it_is_skipped_during_parsing(self):
        html_text = """
          <div>
            <hr/>
            <figure>
              <img src="/media/cc0-images/elephant-660-480.jpg" alt="Elephant at sunset" />
              <figcaption>An elephant at sunset</figcaption>
            </figure>
            <p>Content we want.</p>
          </div>
          """
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        assert list(div.iter_elements()) == [NarrativeText("Content we want.")]


# -- PHRASING (INLINE) ELEMENTS ------------------------------------------------------------------


class DescribePhrasing:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Phrasing`.

    The `Phrasing` class provides most behaviors for phrasing (inline) elements.
    """

    def it_knows_it_is_a_phrasing_element(self):
        b = etree.fromstring("<b>Hello</b>", html_parser).xpath(".//b")[0]

        assert isinstance(b, Phrasing)
        assert b.is_phrasing is True

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            # -- an empty element produces no text segments --
            ("<code></code>", []),
            # -- element text produces one segment --
            ("<data> foo </data>", [(" foo ", {})]),
            # -- element tail produces one segment --
            ("<dfn/> bar ", [(" bar ", {})]),
            # -- element descendants each produce one segment --
            ("<kbd><mark>foo <meter>bar</meter></mark></kbd>", [("foo ", {}), ("bar", {})]),
            # -- and any combination produces a segment for each text, child, and tail --
            (
                "<kbd> <mark>foo <meter>bar</meter> baz</mark> </kbd>",
                [
                    (" ", {}),
                    ("foo ", {}),
                    ("bar", {}),
                    (" baz", {}),
                    (" ", {}),
                ],
            ),
        ],
    )
    def it_generates_text_segments_for_its_text_and_children_and_tail(
        self, html_text: str, expected_value: list[TextSegment]
    ):
        e = etree.fromstring(html_text, html_parser).xpath(".//body")[0][0]
        assert list(e.iter_text_segments()) == expected_value

    def it_forms_its_annotations_from_emphasis(self):
        cite = etree.fromstring("<cite>  rhombus </cite>", html_parser).xpath(".//cite")[0]
        assert cite._annotation(cite.text, "bi") == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "bi",
        }

    def but_not_when_text_is_empty_or_whitespace(self):
        cite = etree.fromstring("<cite>   </cite>", html_parser).xpath(".//cite")[0]
        assert cite._annotation(cite.text, "bi") == {}

    def and_not_when_there_is_no_emphasis(self):
        cite = etree.fromstring("<cite>rhombus</cite>", html_parser).xpath(".//cite")[0]
        assert cite._annotation(cite.text, "") == {}

    def it_uses_the_enclosing_emphasis_as_the_default_inside_emphasis(self):
        abbr = etree.fromstring("<abbr>LLM</abbr>", html_parser).xpath(".//abbr")[0]
        assert abbr._inside_emphasis("xyz") == "xyz"


class DescribeBold:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Bold`.

    The `Bold` class is used for `<b>` and `<strong>` tags and adds emphasis metadata.
    """

    def it_annotates_its_text_segment_with_bold_emphasis(self):
        b = etree.fromstring("<b>rhombus</b>", html_parser).xpath(".//b")[0]

        text_segments = b.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus"
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "b",
        }

    def and_its_children_are_also_annotated_with_bold_emphasis(self):
        b = etree.fromstring("<b>rhombus <i>pentagon</i></b>", html_parser).xpath(".//b")[0]

        text_segments = b.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus "
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "b",
        }
        text, annotation = next(text_segments)
        assert text == "pentagon"
        assert annotation == {
            "emphasized_text_contents": "pentagon",
            "emphasized_text_tags": "bi",
        }

    def but_not_its_tail(self):
        b = etree.fromstring("<b>rhombus</b> pentagon", html_parser).xpath(".//b")[0]

        text_segments = b.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus"
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "b",
        }
        text, annotation = next(text_segments)
        assert text == " pentagon"
        assert annotation == {}


class DescribeItalic:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Italic`.

    The `Italic` class is used for `<i>` and `<em>` tags and adds emphasis metadata.
    """

    def it_annotates_its_text_segment_with_italic_emphasis(self):
        i = etree.fromstring("<i>rhombus</i>", html_parser).xpath(".//i")[0]

        text_segments = i.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus"
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "i",
        }

    def and_its_children_are_also_annotated_with_italic_emphasis(self):
        em = etree.fromstring("<em>rhombus <b>pentagon</b></em>", html_parser).xpath(".//em")[0]

        text_segments = em.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus "
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "i",
        }
        text, annotation = next(text_segments)
        assert text == "pentagon"
        assert annotation == {
            "emphasized_text_contents": "pentagon",
            "emphasized_text_tags": "bi",
        }

    def but_not_its_tail(self):
        i = etree.fromstring("<i>rhombus</i> pentagon", html_parser).xpath(".//i")[0]

        text_segments = i.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus"
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "i",
        }
        text, annotation = next(text_segments)
        assert text == " pentagon"
        assert annotation == {}


class DescribeLineBreak:
    """Isolated unit-test suite for `unstructured.partition.html.parser.LineBreak`.

    Used for `<br/>` elements, it's only special behavior is to add whitespace such that phrasing
    butted up tight on both sides of the `<br/>` element is not joined, like `abc<br/>def` should
    become "abc def", not "abcdef".
    """

    def it_adds_a_newline_in_its_place(self):
        cite = etree.fromstring(
            "<cite>spaceships of the<br/>Vogon Constructor Fleet</cite>", html_parser
        ).xpath(".//cite")[0]

        text_segments = cite.iter_text_segments()

        texts = [ts.text for ts in text_segments]
        assert texts == ["spaceships of the", "\n", "Vogon Constructor Fleet"]
        assert _normalize_text("".join(texts)) == "spaceships of the Vogon Constructor Fleet"


class DescribeRemovedPhrasing:
    """Isolated unit-test suite for `unstructured.partition.html.parser.RemovedPhrasing`.

    Used for phrasing elements like `<label>` that we want to skip, including any content they
    enclose. The tail of such an element is not skipped though.
    """

    def it_behaves_like_an_empty_element(self):
        label = etree.fromstring(
            "<div>\n"
            "  <label>Space<p>is big</p>, <b>mind-bogglingly</b> big.</label>\n"
            "  Like vastly, hugely big.\n"
            "</div>",
            html_parser,
        ).xpath(".//label")[0]

        (text_segment,) = list(label.iter_text_segments())

        assert isinstance(label, RemovedPhrasing)
        assert label.is_phrasing is True
        assert text_segment.text == "\n  Like vastly, hugely big.\n"


# -- DUAL-ROLE ELEMENTS --------------------------------------------------------------------------


class DescribeAnchor:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Anchor`.

    The `Anchor` class is used for `<a>` tags and provides link metadata.
    """

    # -- .is_phrasing -----------------------------------------------------

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            # -- an empty <a> identifies as phrasing --
            ('<a href="http://eie.io"></a>', True),
            # -- an <a> with text but no children identifies as phrasing --
            ('<a href="http://eie.io">“O Deep Thought computer," he said,</a>', True),
            # -- an <a> with no text and only phrasing children identifies as phrasing --
            ('<a href="http://eie.io"><i>“O Deep Thought computer,"</i></a>', True),
            # -- an <a> with both text and phrasing children identifies as phrasing --
            ('<a href="http://eie.io">“O <b>Deep Thought</b> computer,"</a>', True),
            # -- but an <a> with a block-item child does not --
            ('<a href="http://eie.io"><p>“O Deep Thought computer,"</p></a>', False),
            # -- and an <a> with both text and a block-item child does not --
            ('<a href="http://eie.io">“O Deep Thought computer,"<div>he said,</div></a>', False),
            # -- and an <a> with text and both block and phrasing children does not --
            ('<a href="http://eie.io">“O <b>Deep</b> Thought <div>computer," he</div></a>', False),
        ],
    )
    def it_determines_whether_it_is_phrasing_dynamically(
        self, html_text: str, expected_value: bool
    ):
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        assert isinstance(a, Anchor)
        assert a.is_phrasing is expected_value

    # -- .iter_elements() -------------------------------------------------

    def it_can_also_act_as_a_block_item(self):
        html_text = """
        <div>
          <a href="http://eie.io">
            O Deep Thought computer, he said,
            <div>The task we have designed you to perform is this.</div>
            <p>We want you to tell us.... he paused,</p>
          </a>
        </div>
        """
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        elements = a.iter_elements()

        assert [e.text for e in elements] == [
            "O Deep Thought computer, he said,",
            "The task we have designed you to perform is this.",
            "We want you to tell us.... he paused,",
        ]

    # -- .iter_text_segments() --------------------------------------------

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            # -- produces no text-segment or annotation for anchor.text when there is none --
            ('<a href="http://abc.com"></a>', []),
            # -- but it produces a text-segment for the tail if there is one --
            ('<a href="http://abc.com"></a> long tail ', [TextSegment(" long tail ", {})]),
            # -- produces text-segment but no annotation for anchor.text when it is whitespace --
            ('<a href="http://abc.com">  </a>', [TextSegment("  ", {})]),
            # -- produces text-segment and annotation for anchor text
            # -- Note link-texts annotation is whitespace-normalized but text-segment text is not.
            (
                '<a href="http://abc.com"> click here </a>',
                [
                    TextSegment(
                        " click here ",
                        {"link_texts": ["click here"], "link_urls": ["http://abc.com"]},
                    )
                ],
            ),
            # -- produces text-segment for both text and tail when present --
            (
                '<a href="http://abc.com"> click here </a> long tail',
                [
                    TextSegment(
                        " click here ",
                        {"link_texts": ["click here"], "link_urls": ["http://abc.com"]},
                    ),
                    TextSegment(" long tail", {}),
                ],
            ),
            # -- nested phrasing inside <a> element is handled as expected --
            (
                '<p>I am <a href="http://eie.io">one <u>with<i> the</i></u> Force</a>.</p>',
                [
                    TextSegment(
                        "one with the Force",
                        {
                            "emphasized_text_contents": ["the"],
                            "emphasized_text_tags": ["i"],
                            "link_texts": ["one with the Force"],
                            "link_urls": ["http://eie.io"],
                        },
                    ),
                    TextSegment(".", {}),
                ],
            ),
        ],
    )
    def it_generates_link_annotated_text_segments_for_its_text_and_a_tail_text_segment(
        self, html_text: str, expected_value: list[TextSegment]
    ):
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]
        assert list(a.iter_text_segments()) == expected_value


# -- DEFAULT ELEMENT -----------------------------------------------------------------------------


class DescribeDefaultElement:
    """Isolated unit-test suite for `unstructured.partition.html.parser.DefaultElement`.

    Used for any element we haven't assigned a custom element-class too. This prominently includes
    any non-HTML elements that can be embedded in the HTML.

    It identifies as a block item but it can behave as either a block-item or phrasing. Its behavior
    is a combination of RemovedBlock and RemovedPhrasing. Namely, it iterates zero elements and only
    iterates a text-segment for its tail.
    """

    # -- .is_phrasing -----------------------------------------------------

    def it_identifies_as_a_phrasing_element(self):
        foobar = etree.fromstring("<foobar>Vogon</foobar>", html_parser).xpath(".//foobar")[0]

        assert isinstance(foobar, DefaultElement)
        assert foobar.is_phrasing is True

    # -- .iter_elements() -------------------------------------------------

    def it_generates_zero_elements_as_a_block_item(self):
        """Should never be called but belts and suspenders."""
        foobar = etree.fromstring(
            "<foobar>Space<p>is big</p>, <b>mind-bogglingly</b> big.</foobar>",
            html_parser,
        ).xpath(".//foobar")[0]

        elements = foobar.iter_elements()

        with pytest.raises(StopIteration):
            next(elements)

    # -- .iter_text_segments() --------------------------------------------

    def it_generates_its_tail_but_no_inner_text_segments_when_called_like_phrasing(self):
        foobar = etree.fromstring(
            "<div>\n"
            "  O Deep Thought computer, he said,\n"
            "  <foobar>Vogon Constructor Fleet</foobar>\n"
            "  The task we have designed you to perform is this.\n"
            "  <p>We want you to tell us.... he paused,</p>\n"
            "</div>",
            html_parser,
        ).xpath(".//foobar")[0]

        texts = [ts.text for ts in foobar.iter_text_segments()]

        assert texts == ["\n  The task we have designed you to perform is this.\n  "]

    def and_it_behaves_like_an_empty_phrasing_element_inside_a_block_element(self):
        div = etree.fromstring(
            "<div>\n"
            "  O Deep Thought computer, he said,\n"
            "  <foobar>Vogon Constructor Fleet</foobar>\n"
            "  The task we have designed you to perform is this.\n"
            "  <p>We want you to tell us.... he paused,</p>\n"
            "</div>",
            html_parser,
        ).xpath(".//div")[0]

        texts = [e.text for e in div.iter_elements()]

        assert texts == [
            "O Deep Thought computer, he said, The task we have designed you to perform is this.",
            "We want you to tell us.... he paused,",
        ]
