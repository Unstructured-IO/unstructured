from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from markdown import markdown

from unstructured.documents.elements import CodeSnippet, NarrativeText, Title
from unstructured.staging.base import (
    create_file_from_elements,
    element_to_md,
    elements_from_dicts,
    elements_to_md,
)


@pytest.mark.parametrize(
    "text",
    [
        'print("hello")',
        'if ready:\n    print("hello")\n',
        "# a comment\n**literal asterisks**",
        '<script>alert("example")</script>',
        "<tag>&lt;entity&gt;</tag>",
        "```\n# a fenced-code example\n```",
        "````\n```nested```\n````\n",
        "~~~\n# a tilde-fence example\n~~~",
        "line one\n\nline three\n\n",
        "    indentation\n  more indentation  ",
        "",
    ],
)
def test_code_snippets_render_as_one_complete_markdown_code_block(text: str):
    element = CodeSnippet(text, element_id="code")
    before = element.to_dict()

    result = element_to_md(element)

    soup = BeautifulSoup(markdown(result, extensions=["fenced_code"]), "html.parser")
    assert len(soup.find_all("pre")) == 1
    assert len(soup.find_all("code")) == 1
    assert soup.pre.code.get_text() == (text if not text or text.endswith("\n") else text + "\n")
    assert soup.find(["script", "h1", "strong", "tag"]) is None
    assert element.to_dict() == before


def test_code_block_keeps_surrounding_document_content_separate():
    elements = [
        Title("Guide"),
        NarrativeText("Before the example."),
        CodeSnippet("# not a heading\nprint('first')"),
        CodeSnippet("print('second')"),
        NarrativeText("After the example."),
    ]

    result = elements_to_md(iter(elements))

    soup = BeautifulSoup(markdown(result, extensions=["fenced_code"]), "html.parser")
    assert [tag.name for tag in soup.find_all(recursive=False)] == ["h1", "p", "pre", "pre", "p"]
    assert [code.get_text() for code in soup.find_all("code")] == [
        "# not a heading\nprint('first')\n",
        "print('second')\n",
    ]
    assert [paragraph.get_text() for paragraph in soup.find_all("p")] == [
        "Before the example.",
        "After the example.",
    ]


@pytest.mark.parametrize("entrypoint", [elements_to_md, create_file_from_elements])
def test_deserialized_code_survives_markdown_file_export(entrypoint, tmp_path: Path):
    text = 'print("café <example>")'
    elements = elements_from_dicts(
        [{"type": "CodeSnippet", "element_id": "code", "text": text, "metadata": {}}]
    )
    destination = tmp_path / "example.md"

    result = entrypoint(iter(elements), filename=str(destination), encoding="latin-1")

    assert destination.read_text(encoding="latin-1") == result
    soup = BeautifulSoup(markdown(result, extensions=["fenced_code"]), "html.parser")
    assert soup.pre.code.get_text() == text + "\n"


def test_code_export_keeps_original_tabs_and_line_endings():
    text = "if ready:\r\n\tprint('example')\r\n"

    result = element_to_md(CodeSnippet(text))

    assert result == "```\n" + text + "```"


def test_ordinary_text_keeps_its_existing_markdown_rendering():
    text = "# Heading\n**emphasis**"

    assert element_to_md(NarrativeText(text)) == text
