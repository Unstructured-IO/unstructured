from __future__ import annotations

import pathlib
import re
from typing import Any
from unittest.mock import patch

import pytest
from markdown.extensions.fenced_code import FencedCodeExtension
from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementType, Title
from unstructured.partition.auto import partition
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
    """User can override markdown extensions via `extensions` kwarg (fixes #4006)."""
    text = """```bash
# create the container
docker run -dt --name unstructured downloads.unstructured.io/unstructured-io/unstructured:latest
```"""

    expected_body = (
        "# create the container\n"
        "docker run -dt --name unstructured "
        "downloads.unstructured.io/unstructured-io/unstructured:latest"
    )

    # Without fenced_code, ``#`` inside the fence is parsed as a heading (undesired).
    elements_tables_only = partition_md(text=text, extensions=["tables"])
    assert any(isinstance(el, Title) for el in elements_tables_only)

    # Default and explicit fenced_code keep the block as one element (CodeSnippet from HTML).
    assert len(partition_md(text=text)) == 1
    elements_fenced = partition_md(text=text, extensions=["fenced_code"])
    assert len(elements_fenced) == 1
    assert elements_fenced[0].category == ElementType.CODE_SNIPPET
    assert elements_fenced[0].text == expected_body

    # Extension instances (normal Python-Markdown API) match string extension names.
    elements_instance = partition_md(text=text, extensions=[FencedCodeExtension()])
    assert elements_instance == elements_fenced


def test_partition_md_extensions_not_list_raises():
    with pytest.raises(ValueError, match="'extensions' must be a list"):
        partition_md(text="# Hi", extensions=("tables",))  # type: ignore[arg-type]


def test_partition_md_extensions_invalid_item_raises():
    with pytest.raises(ValueError, match="Each entry in 'extensions'"):
        partition_md(text="# Hi", extensions=[42])  # type: ignore[list-item]


def test_partition_md_tables_only_differs_from_default_for_code_fence():
    """Without ``fenced_code``, ``#`` inside a fence can become a Title (see #4006)."""
    text = """```bash
# line
```"""
    default_el = partition_md(text=text)[0]
    tables_only_els = partition_md(text=text, extensions=["tables"])
    assert default_el.category == ElementType.CODE_SNIPPET
    assert any(e.category == ElementType.TITLE for e in tables_only_els)


# -- YAML front matter --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "front_matter",
    [
        # -- one line: without stripping, this became a setext heading that parented the body --
        "---\ntitle: Getting started\n---\n",
        "---\ntitle: Getting started\nsidebar_position: 2\ntags: [setup, install]\n---\n",
        "---\r\ntitle: Getting started\r\n---\r\n",
        "﻿---\ntitle: Getting started\n---\n",
        "---\nlayout: post\n...\n",
        '---\ntitle: "Setup: part 1"\ndate: 2026-11-17T10:00:00Z\nurl: https://example.com/a\n---\n',
        "---\ntags:\n  - setup\n  - install\nauthors:\n- name: Ada\n  url: https://example.com\n---\n",
        "---\nseo:\n  title: Setup\ndescription: >-\n  How to: install\ndraft:\n---\n",
    ],
)
def test_partition_md_skips_yaml_front_matter(front_matter: str):
    body = "\n## Install\n\nInstall the package and run the server.\n"

    elements = partition_md(text=front_matter + body)

    assert [(e.category, e.text) for e in elements] == [
        (ElementType.TITLE, "Install"),
        (ElementType.NARRATIVE_TEXT, "Install the package and run the server."),
    ]
    assert elements[1].metadata.parent_id == elements[0].id


@pytest.mark.parametrize(
    "prefix",
    [
        # -- colon-bearing prose --
        "Notice: This section describes an incident.\n",
        "See also: the install guide.\n",
        "note: the server restarts: save your work first.\n",
        "summary: first line\nand the paragraph goes on.\n",
        "warning: *do not* do this.\n\nlater: more prose.\n",
        # -- headings, which look like YAML comments --
        "# Incident report\n",
        "# Incident report\nstatus: open\n",
        "status: open\n## Impact\n",
        # -- a heading and body text between two thematic breaks --
        "Notice: An incident.\n\n## Impact\n\nThe service was down.\n\n",
        "status: open\n\n## Impact\n\nThe service was down.\n\n",
        # -- not a valid YAML mapping --
        "title: one\ntitle: two\n",
        "tags: [setup,\n",
    ],
)
def test_partition_md_keeps_content_between_thematic_breaks(prefix: str):
    text = f"---\n{prefix}---\n\nThe body of the document.\n"

    elements = partition_md(text=text)

    unchanged = partition_md(text=text, skip_front_matter=False)
    assert [(e.category, e.text) for e in elements] == [(e.category, e.text) for e in unchanged]
    joined = " ".join(e.text for e in elements)
    for word in re.findall(r"\w+", prefix):
        assert word in joined
    assert elements[-1].text == "The body of the document."


def test_partition_md_can_keep_front_matter():
    text = "---\ntitle: Getting started\n---\n\nInstall the package.\n"

    elements = partition_md(text=text, skip_front_matter=False)

    assert [e.text for e in elements] == ["title: Getting started", "Install the package."]


def test_auto_partition_md_forwards_skip_front_matter(tmp_path: pathlib.Path):
    path = tmp_path / "doc.md"
    path.write_text("---\ntitle: Getting started\n---\n\nInstall the package.\n")

    assert [e.text for e in partition(str(path))] == ["Install the package."]
    assert "title: Getting started" in [
        e.text for e in partition(str(path), skip_front_matter=False)
    ]


def test_partition_md_keeps_a_leading_thematic_break_that_is_not_front_matter():
    elements = partition_md(text="---\nIntroduction\n---\n\nThe body of the document.\n")

    assert [e.text for e in elements] == ["Introduction", "The body of the document."]


def test_partition_md_keeps_a_front_matter_like_block_that_is_not_at_the_start():
    elements = partition_md(text="# Notes\n\n---\ntitle: kept\n---\n")

    assert "title: kept" in [e.text for e in elements]
