import pytest
from bs4 import BeautifulSoup

from unstructured.documents.ontology import Paragraph
from unstructured.partition.html.transformations import (
    RECURSION_LIMIT,
    ontology_to_unstructured_elements,
    parse_html_to_ontology,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "<p>Use &lt;code&gt; for inline text and &lt;br&gt; for a line break</p>",
            "Use <code> for inline text and <br> for a line break",
        ),
        ("<code>std::vector&lt;int&gt; values;</code>", "std::vector<int> values;"),
        ("<code>&lt;div&gt;example&lt;/div&gt;</code>", "<div>example</div>"),
        ("<p>&lt;!-- an HTML comment --&gt;</p>", "<!-- an HTML comment -->"),
        ("<p>&#60;span&#62;example&#60;/span&#62;</p>", "<span>example</span>"),
        ("<p>R&amp;D &amp;lt;tag&amp;gt;</p>", "R&D &lt;tag&gt;"),
        ("<p>1 &lt; 2 and 3 &gt; 2</p>", "1 < 2 and 3 > 2"),
        (
            "<p>Use &lt;br&gt; <b>without</b> an end tag</p>",
            "Use <br> without an end tag",
        ),
        (
            "<p><b>Write</b> &lt;code&gt; <i>around</i> examples</p>",
            "Write <code> around examples",
        ),
        (
            "<unknown>Use &lt;br&gt; <b>without</b> an end tag</unknown>",
            "Use <br>\nwithout\nan end tag",
        ),
    ],
)
def test_v2_preserves_literal_markup_in_text(source: str, expected: str):
    document = parse_html_to_ontology(f'<body class="Document">{source}</body>')

    assert document.to_text() == expected
    elements = ontology_to_unstructured_elements(document)
    assert [element.text for element in elements] == [expected]


@pytest.mark.parametrize(
    "literal",
    [
        '<img src="x" onerror="alert(1)">',
        "<script>alert(1)</script>",
        '<iframe src="https://example.com"></iframe>',
    ],
)
def test_literal_markup_stays_inert_in_generated_html(literal: str):
    import html

    document = parse_html_to_ontology(
        f'<body class="Document"><p>{html.escape(literal)}</p></body>'
    )

    assert document.to_text() == literal
    for rendered in (
        document.to_html(),
        ontology_to_unstructured_elements(document)[0].metadata.text_as_html,
    ):
        soup = BeautifulSoup(rendered, "html.parser")
        assert soup.get_text(strip=True) == literal
        assert soup.find(["img", "script", "iframe"]) is None


@pytest.mark.parametrize("depth", [RECURSION_LIMIT - 1, RECURSION_LIMIT + 10])
def test_literal_text_survives_at_and_beyond_the_recursion_limit(depth: int):
    source = "Use &lt;code&gt; here"
    for _ in range(depth):
        source = f'<p class="Paragraph">{source}</p>'
    document = parse_html_to_ontology(f'<body class="Document">{source}</body>')

    assert document.to_text() == "Use <code> here"
    assert [element.text for element in ontology_to_unstructured_elements(document)] == [
        "Use <code> here"
    ]


def test_editing_parsed_text_and_copying_an_ontology_keeps_literal_text():
    document = parse_html_to_ontology('<body class="Document"><p>Original</p></body>')
    paragraph = document.children[0]
    paragraph.text = "Use <br> here"

    assert paragraph.to_text() == "Use <br> here"
    assert document.model_copy(deep=True).to_text() == "Use <br> here"


def test_explicit_markup_text_keeps_its_existing_behavior():
    paragraph = Paragraph(text="Before <b>bold</b> after")

    assert paragraph.to_text() == "Before bold after"
