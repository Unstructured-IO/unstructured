"""HTML exports keep the layout and literal text of code snippets."""

import pytest
from bs4 import BeautifulSoup

from unstructured.documents.elements import CodeSnippet, ElementMetadata, Text
from unstructured.partition.html.convert import elements_to_html


@pytest.mark.parametrize(
    "text",
    [
        "if ready:\n    run()\n    finish()",
        "def calculate():\n\treturn 1\n",
        '<div title="x & y">literal HTML</div>\n',
        "\n\n# Keep leading blank lines\nvalue = 2\n",
    ],
)
def test_code_snippets_render_as_preformatted_literal_text(text):
    element = CodeSnippet(text, element_id="code")

    output = elements_to_html([element], no_group_by_page=True)
    soup = BeautifulSoup(output, "html.parser")
    pre = soup.find("pre", id="code")

    assert pre is not None
    assert pre.find("code") is not None
    assert pre.get_text() == text
    assert pre.find("div") is None


def test_explicit_code_html_is_preserved():
    element = CodeSnippet(
        "fallback",
        metadata=ElementMetadata(text_as_html="<pre><code>provided\n  code</code></pre>"),
    )

    output = elements_to_html([element], no_group_by_page=True)

    assert BeautifulSoup(output, "html.parser").find("pre").get_text() == "provided\n  code"


def test_ordinary_text_keeps_its_paragraph_representation():
    output = elements_to_html([Text("Ordinary text")], no_group_by_page=True)
    soup = BeautifulSoup(output, "html.parser")

    assert soup.find("pre") is None
    assert soup.find("p").get_text(strip=True) == "Ordinary text"
