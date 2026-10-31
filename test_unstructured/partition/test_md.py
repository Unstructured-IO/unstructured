from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementType, Title
from unstructured.partition.md import partition_md
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA


@pytest.mark.parametrize("marker", ["1.", "-"])
@pytest.mark.parametrize("separator", ["\n", "\n\n"])
def test_partition_md_recognizes_loose_and_tight_lists(marker: str, separator: str):
    text = separator.join(f"{marker} list item {word}." for word in ["one", "two", "three"])

    elements = partition_md(text=text, languages=[""])

    assert [e.category for e in elements] == ["ListItem"] * 3
    assert [e.text for e in elements] == [f"list item {word}." for word in ["one", "two", "three"]]
    assert [e.metadata.category_depth for e in elements] == [1, 1, 1]


def test_partition_md_from_filename():
    filename = example_doc_path("README.md")
    elements = partition_md(filename=filename)

    assert len(elements) > 0
    assert "PageBreak" not in [elem.category for elem in elements]
    assert isinstance(elements[0], Title)
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"md"}


def test_partition_md_from_file():
    filename = example_doc_path("README.md")
    with open(filename, "rb") as f:
        elements = partition_md(file=f)
    assert len(elements) > 0


def test_partition_md_from_text():
    with open(example_doc_path("README.md")) as f:
        text = f.read()

    elements = partition_md(text=text)

    assert len(elements) > 0
    assert all(e.metadata.filename is None for e in elements)


def test_partition_md_from_text_works_with_empty_string():
    assert partition_md(text="") == []


def test_partition_md_with_whitespace_text_still_validates_extensions():
    with pytest.raises(ValueError, match="Each entry in 'extensions'"):
        partition_md(text=" \n\t", extensions=[42])


class MockResponse:
    def __init__(self, text: str, status_code: int, headers: dict[str, Any] = {}):
        self.text = text
        self.status_code = status_code
        self.ok = status_code < 300
        self.headers = headers


def test_partition_md_from_url():
    filename = example_doc_path("README.md")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(
        text=text,
        status_code=200,
        headers={"Content-Type": "text/markdown"},
    )
    with patch("unstructured.partition.md.safe_get", return_value=response) as _:
        elements = partition_md(url="https://fake.url")

    assert len(elements) > 0
    assert all(e.metadata.filename is None for e in elements)


def test_partition_md_from_url_raises_with_bad_status_code():
    filename = example_doc_path("README.md")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(
        text=text,
        status_code=500,
        headers={"Content-Type": "text/html"},
    )
    with (
        patch("unstructured.partition.md.safe_get", return_value=response) as _,
        pytest.raises(ValueError),
    ):
        partition_md(url="https://fake.url")


def test_partition_md_from_url_raises_with_bad_content_type():
    filename = example_doc_path("README.md")
    with open(filename) as f:
        text = f.read()

    response = MockResponse(
        text=text,
        status_code=200,
        headers={"Content-Type": "application/json"},
    )
    with (
        patch("unstructured.partition.md.safe_get", return_value=response) as _,
        pytest.raises(ValueError),
    ):
        partition_md(url="https://fake.url")


def test_partition_md_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_md()


def test_partition_md_raises_with_too_many_specified():
    filename = example_doc_path("README.md")
    with open(filename) as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_md(filename=filename, text=text)


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_md_from_filename_gets_filename_from_filename_arg():
    elements = partition_md(example_doc_path("README.md"))

    assert len(elements) > 0
    assert all(e.metadata.filename == "README.md" for e in elements)


def test_partition_md_from_file_gets_filename_None():
    with open(example_doc_path("README.md"), "rb") as f:
        elements = partition_md(file=f)

    assert len(elements) > 0
    assert all(e.metadata.filename is None for e in elements)


def test_partition_md_from_filename_prefers_metadata_filename():
    elements = partition_md(example_doc_path("README.md"), metadata_filename="orig-name.md")

    assert len(elements) > 0
    assert all(element.metadata.filename == "orig-name.md" for element in elements)


def test_partition_md_from_file_prefers_metadata_filename():
    with open(example_doc_path("README.md"), "rb") as f:
        elements = partition_md(file=f, metadata_filename="orig-name.md")

    assert all(e.metadata.filename == "orig-name.md" for e in elements)


# -- .metadata.filetype --------------------------------------------------------------------------


def test_partition_md_gets_the_MD_MIME_type_in_metadata_filetype():
    MD_MIME_TYPE = "text/markdown"
    elements = partition_md(example_doc_path("README.md"))
    assert all(e.metadata.filetype == MD_MIME_TYPE for e in elements), (
        f"Expected all elements to have '{MD_MIME_TYPE}' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_md_from_file_path_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.md.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_md(example_doc_path("README.md"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_md_from_file_gets_last_modified_None():
    with open(example_doc_path("README.md"), "rb") as f:
        elements = partition_md(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_md_from_text_gets_last_modified_None():
    with open(example_doc_path("README.md")) as f:
        text = f.read()

    elements = partition_md(text=text)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_md_from_file_path_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.md.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_md(
        example_doc_path("README.md"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_md_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("README.md"), "rb") as f:
        elements = partition_md(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_md_from_text_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("README.md")) as f:
        text = f.read()

    elements = partition_md(text=text, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_md_with_json():
    with open(example_doc_path("README.md")) as f:
        text = f.read()
    elements = partition_md(text=text)
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_by_title_on_partition_md():
    filename = example_doc_path("README.md")
    elements = partition_md(filename)
    chunk_elements = partition_md(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)

    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_md_element_metadata_has_languages():
    filename = "example-docs/README.md"
    elements = partition_md(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_md_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.md"
    elements = partition_md(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]


def test_partition_md_languages_empty_disables_detection():
    """Passing languages=[\"\"] disables language detection (no metadata.languages set)."""
    filename = "example-docs/README.md"
    elements = partition_md(filename=filename, languages=[""])
    # When detection is disabled, metadata.languages should not be set (None)
    for el in elements:
        assert el.metadata.languages is None


def test_partition_md_parse_table():
    filename = example_doc_path("simple-table.md")
    elements = partition_md(filename=filename)
    assert len(elements) > 0
    assert elements[0].category == ElementType.TABLE


@pytest.mark.parametrize("filename", ["umlauts-utf8.md", "umlauts-non-utf8.md"])
def test_partition_md_with_umlauts(filename: str):
    filename = example_doc_path(filename)
    elements = partition_md(filename=filename)
    assert len(elements) > 0
    assert elements[-1].text.endswith("äöüß")


def test_partition_md_xml_processing_instruction():
    xml_content = """```
<?xml version="1.0"?>
<sparql xmlns="http://www.w3.org/2005/sparql-results#">
  <head></head>
  <boolean>true</boolean>
</sparql>
```"""

    elements = partition_md(text=xml_content)
    assert len(elements) == 1


def test_partition_md_xml_processing_instruction_with_indents():
    xml_content = """```
  <?xml version="1.0"?>
<sparql xmlns="http://www.w3.org/2005/sparql-results#">
  <head></head>
  <boolean>true</boolean>
</sparql>
```"""

    elements = partition_md(text=xml_content)
    assert len(elements) == 1


def test_partition_md_non_xml_processing_instruction():
    php_content = """```
    <?php echo "hello"; ?>
    ```"""

    elements = partition_md(text=php_content)
    assert len(elements) == 1


def test_partition_fenced_code():
    filename = example_doc_path("codeblock.md")
    elements = partition_md(filename=filename)

    # Should have 5 elements: 2 titles and 3 code blocks
    assert len(elements) == 5

    assert elements[0].text == "HTML Example"

    expected_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sample HTML</title>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>This is a simple HTML example.</p>
</body>
</html>"""
    assert elements[1].text == expected_html

    assert elements[2].text == "XML Example"

    expected_xml = """<note>
    <to>Tove</to>
    <from>Jani</from>
    <heading>Reminder</heading>
    <body>Don't forget me this weekend!</body>
</note>"""
    assert elements[3].text == expected_xml

    assert elements[4].text == expected_xml


def test_partition_md_custom_extensions_parameter():
    """User can override markdown extensions via `extensions` kwarg (fixes #4006).

    Since the CommonMark switch for #3280, fenced code blocks are always parsed
    as code: the old tables-only behavior (``#`` inside a fence becoming a Title)
    no longer exists, so tables-only now matches the default for fenced code.
    """
    text = """```bash
# create the container
docker run -dt --name unstructured downloads.unstructured.io/unstructured-io/unstructured:latest
```"""

    expected_body = (
        "# create the container\n"
        "docker run -dt --name unstructured "
        "downloads.unstructured.io/unstructured-io/unstructured:latest"
    )

    # Default, explicit fenced_code, and tables-only all keep the block as one
    # CodeSnippet element (fenced code is part of CommonMark, always parsed).
    assert len(partition_md(text=text)) == 1
    elements_fenced = partition_md(text=text, extensions=["fenced_code"])
    assert len(elements_fenced) == 1
    assert elements_fenced[0].category == ElementType.CODE_SNIPPET
    assert elements_fenced[0].text == expected_body
    elements_tables_only = partition_md(text=text, extensions=["tables"])
    assert len(elements_tables_only) == 1
    assert elements_tables_only[0].category == ElementType.CODE_SNIPPET
    assert elements_tables_only[0].text == expected_body


def test_partition_md_extensions_not_list_raises():
    with pytest.raises(ValueError, match="'extensions' must be a list"):
        partition_md(text="# Hi", extensions=("tables",))  # type: ignore[arg-type]


def test_partition_md_extensions_invalid_item_raises():
    with pytest.raises(ValueError, match="Each entry in 'extensions'"):
        partition_md(text="# Hi", extensions=[42])  # type: ignore[list-item]


def test_partition_md_tables_only_matches_default_for_code_fence():
    """Since the CommonMark switch for #3280, fenced code is always parsed, so
    the old tables-only/``#``-becomes-Title behavior (see #4006) is gone."""
    text = """```bash
# line
```"""
    default_el = partition_md(text=text)[0]
    tables_only_els = partition_md(text=text, extensions=["tables"])
    assert default_el.category == ElementType.CODE_SNIPPET
    assert len(tables_only_els) == 1
    assert tables_only_els[0].category == ElementType.CODE_SNIPPET


# -- #3280: list block after an intro line ---------------------------------------


def test_partition_md_list_after_intro_line_parses_as_list():
    """Fixes #3280: a list block following an intro line must parse as a list,
    not fold into one blob. The no-blank-line form must match the blank-line
    form, which was already correct."""
    text = (
        "# header 1\n"
        "## header 2\n"
        "My list\n"
        "- item 1\n"
        "- item 2\n"
        "- item 3\n"
        "- item 4\n"
        "- item 5\n"
        "## header 3\n"
    )
    blank_text = text.replace("My list\n- item 1", "My list\n\n- item 1")
    elements = partition_md(text=text, languages=[""])
    blank_elements = partition_md(text=blank_text, languages=[""])
    assert [e.category for e in elements] == [e.category for e in blank_elements]
    assert [e.category for e in elements if e.text.startswith("item")] == ["ListItem"] * 5
    assert not any("item" in e.text for e in elements if e.category == "Title")


def test_partition_md_list_after_intro_line_chunks_with_its_header():
    """Fixes #3280 downstream: with a tight character budget, the list items
    must chunk with their header, not split away from it as a lone blob."""
    text = "## header 2\nMy list\n- item 1\n- item 2\n- item 3\n- item 4\n- item 5\n## header 3\n"
    elements = partition_md(text=text, languages=[""])
    chunks = chunk_by_title(elements, max_characters=60)
    header2_chunk = [c for c in chunks if "header 2" in c.text]
    assert len(header2_chunk) == 1
    assert "item 1" in header2_chunk[0].text
    assert "item 5" in header2_chunk[0].text
    assert "header 3" not in header2_chunk[0].text


def test_partition_md_single_item_list_after_intro_line():
    elements = partition_md(text="My list\n- only one\n", languages=[""])
    assert [e.category for e in elements if e.text.startswith("only")] == ["ListItem"]


def test_partition_md_ordered_list_after_intro_line():
    elements = partition_md(text="Steps\n1. first\n2. second\n", languages=[""])
    assert [e.category for e in elements if e.text in ("first", "second")] == [
        "ListItem",
        "ListItem",
    ]


def test_partition_md_wrapped_line_follows_commonmark_list_rule():
    """CommonMark tradeoff, pinned not hidden: a wrapped line starting with '*'
    interrupts the paragraph and becomes a list item. This is the parser rule
    the maintainer endorsed for #3280, not the old blank-line-required rule.
    (The first element is UncategorizedText by the same short-line rule that
    gives 'My list' that category; the point pinned here is the list split.)"""
    elements = partition_md(text="The computed value of 7\n* 3 equals 21.\n", languages=[""])
    assert [e.category for e in elements] == ["UncategorizedText", "ListItem"]


def test_partition_md_tables_extension_toggles_table_parsing():
    text = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    assert any(e.category == "Table" for e in partition_md(text=text, languages=[""]))
    assert not any(
        e.category == "Table" for e in partition_md(text=text, extensions=[], languages=[""])
    )


def test_partition_md_unknown_extension_raises():
    with pytest.raises(ValueError, match="not supported"):
        partition_md(text="# Hi", extensions=["toc"])


class _DummyExtension:
    """Stand-in for a Python-Markdown Extension instance: any non-str entry
    must be rejected now that the converter is CommonMark."""


def test_partition_md_python_markdown_extension_instance_raises():
    with pytest.raises(ValueError, match="not supported"):
        partition_md(text="# Hi", extensions=[_DummyExtension()])


def test_partition_md_commonmark_does_not_parse_strikethrough():
    """Documents the parser choice: CommonMark has no strikethrough (a GFM
    extension), so ~~text~~ stays literal. Pins CommonMark, not GFM."""
    elements = partition_md(text="This is ~~not deleted~~ text.\n", languages=[""])
    assert any("~~not deleted~~" in e.text for e in elements)


def test_partition_md_commonmark_does_not_autolink_bare_urls():
    """Documents the parser choice: CommonMark does not autolink bare URLs
    (a GFM extension)."""
    elements = partition_md(text="See https://example.com for details.\n", languages=[""])
    assert any("https://example.com" in e.text for e in elements)
