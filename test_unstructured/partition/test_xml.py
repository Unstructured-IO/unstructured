"""Test-suite for `unstructured.partition.xml` module."""

from __future__ import annotations

import io
import tracemalloc
from typing import Callable

import pytest
from pytest_mock import MockerFixture

from test_unstructured.unit_utils import example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import NarrativeText, Title
from unstructured.partition.json import partition_json
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA
from unstructured.partition.xml import get_leaf_elements, partition_xml
from unstructured.staging.base import elements_to_json


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_filename(filename: str):
    file_path = example_doc_path(filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=False)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"xml"}


def test_partition_xml_from_filename_with_metadata_filename():
    elements = partition_xml(
        example_doc_path("factbook.xml"), xml_keep_tags=False, metadata_filename="test"
    )

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_file(filename: str):
    file_path = example_doc_path(filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename=file_path)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename


def test_partition_xml_from_file_with_metadata_filename():
    with open(example_doc_path("factbook.xml"), "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename="test")

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_file_rb(filename: str):
    file_path = example_doc_path(filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename=file_path)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_filename_with_tags_default_encoding(filename: str):
    file_path = example_doc_path(filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=True)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == filename


def test_partition_xml_from_text_with_tags():
    with open(example_doc_path("factbook.xml")) as f:
        text = f.read()
    elements = partition_xml(text=text, xml_keep_tags=True)

    assert "<leader>Joe Biden</leader>" in elements[0].text


def test_partition_xml_from_filename_with_tags_raises_encoding_error():
    with pytest.raises(UnicodeDecodeError):
        partition_xml(example_doc_path("factbook-utf-16.xml"), xml_keep_tags=True, encoding="utf-8")


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_file_with_tags_default_encoding(filename: str):
    file_path = example_doc_path(filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=True, metadata_filename=file_path)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_file_rb_with_tags_default_encoding(filename: str):
    file_path = example_doc_path(filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=True, metadata_filename=file_path)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == filename


def test_partition_xml_from_file_rb_with_tags_raises_encoding_error():
    with pytest.raises(UnicodeDecodeError):
        with open(example_doc_path("factbook-utf-16.xml"), "rb") as f:
            partition_xml(
                file=f,
                xml_keep_tags=True,
                encoding="utf-8",
            )


# -- .metadata.filetype --------------------------------------------------------------------------


def test_partition_xml_gets_the_XML_mime_type_in_metadata_filetype():
    XML_MIME_TYPE = "application/xml"
    elements = partition_xml(example_doc_path("factbook.xml"))
    assert all(e.metadata.filetype == XML_MIME_TYPE for e in elements), (
        f"Expected all elements to have '{XML_MIME_TYPE}' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_xml_from_file_path_gets_last_modified_from_filesystem(mocker: MockerFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xml.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_xml(filename="example-docs/factbook.xml")

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_xml_from_file_gets_last_modified_None():
    with open("example-docs/factbook.xml", "rb") as f:
        elements = partition_xml(file=f)

    assert elements[0].metadata.last_modified is None


def test_partition_xml_from_file_path_prefers_metadata_last_modified(mocker: MockerFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xml.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_xml(
        filename="example-docs/factbook.xml",
        metadata_last_modified=metadata_last_modified,
    )

    assert elements[0].metadata.last_modified == metadata_last_modified


def test_partition_xml_from_file_prefers_metadata_last_modified():
    with open("example-docs/factbook.xml", "rb") as f:
        elements = partition_xml(file=f, metadata_last_modified="2029-07-05T09:24:28")

    assert elements[0].metadata.last_modified == "2029-07-05T09:24:28"


# ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_with_json(filename: str):
    file_path = example_doc_path(filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=False)
    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert elements[0].metadata.page_number == test_elements[0].metadata.page_number
    assert elements[0].metadata.filename == test_elements[0].metadata.filename

    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


def test_partition_xml_with_narrative_line_breaks():
    xml_text = """<xml>
        <parrot>
            <name>Conure</name>
            <description>A conure is a very friendly bird.
            Conures are feathery and like to dance.
            </description>
        </parrot>
    </xml>"""

    elements = partition_xml(text=xml_text)
    assert elements[0] == Title("Conure")
    assert isinstance(elements[1], NarrativeText)
    assert str(elements[1]).startswith("A conure is a very friendly bird.")
    assert str(elements[1]).strip().endswith("Conures are feathery and like to dance.")


@pytest.mark.parametrize("xml_path", [None, ".//body"])
def test_partition_xml_keeps_text_that_runs_through_child_elements(xml_path: str | None):
    xml_text = (
        "<doc><body><title>Report</title>"
        "<p>The <b>quick</b> brown <i>fox</i> jumps<!-- a comment --> over the dog.</p>"
        "<list><item>One</item><item>Two</item></list></body></doc>"
    )

    elements = partition_xml(text=xml_text, xml_path=xml_path)

    assert [e.text for e in elements] == [
        "Report",
        "The quick brown fox jumps over the dog.",
        "One",
        "Two",
    ]


@pytest.mark.parametrize("xml_path", [None, ".//body"])
@pytest.mark.parametrize(
    ("body", "expected_texts"),
    [
        # -- a record of fields keeps its fields apart, and so does the prose around it --
        (
            "<body>Inventory:<record><name>Alice</name><price>12</price></record>"
            "<record><name>Bob</name><price>34</price></record>Total: 46</body>",
            ["Inventory:", "Alice", "12", "Bob", "34", "Total: 46"],
        ),
        # -- so does a list --
        (
            "<body>Steps:<list><item>Install</item><item>Run</item></list>then check the logs."
            "</body>",
            ["Steps:", "Install", "Run", "then check the logs."],
        ),
        # -- an inline element that wraps another one is still part of the sentence --
        (
            "<body>See <link><label>the docs</label></link> for <b>more</b>.</body>",
            ["See the docs for more."],
        ),
    ],
)
def test_partition_xml_keeps_structural_children_of_prose_apart(
    body: str, expected_texts: list[str], xml_path: str | None
):
    elements = partition_xml(text=f"<doc>{body}</doc>", xml_path=xml_path)

    assert [e.text for e in elements] == expected_texts


def test_partition_xml_reads_a_wrapper_as_the_text_it_wraps():
    # -- the indentation around a lone child is not part of its text --
    xml_text = (
        "<doc>\n  <paragraph>\n    <content>Text one.</content>\n  </paragraph>\n"
        "  <paragraph>\n    <content>Text two.</content>\n  </paragraph>\n</doc>"
    )

    assert list(get_leaf_elements(None, None, xml_text, None)) == ["Text one.", "Text two."]


@pytest.mark.parametrize(
    ("xml_text", "xml_path", "expected_texts"),
    [
        (
            "<doc><section><p>Alpha.</p><p>Beta.</p></section></doc>",
            ".//section | .//p",
            ["Alpha.", "Beta."],
        ),
        ("<doc><section><p>Alpha.</p><p>Beta.</p></section></doc>", ".//*", ["Alpha.", "Beta."]),
        # -- distinct elements with the same text are both kept --
        ("<doc><p>Same.</p><p>Same.</p></doc>", ".//p", ["Same.", "Same."]),
        # -- a comment or processing instruction ahead of the root is not the context node --
        ('<?xml-stylesheet href="s.xsl"?><!-- head --><doc><p>One.</p></doc>', ".//p", ["One."]),
    ],
)
def test_partition_xml_reads_overlapping_xpath_matches_once(
    xml_text: str, xml_path: str, expected_texts: list[str]
):
    elements = partition_xml(text=xml_text, xml_path=xml_path)

    assert [e.text for e in elements] == expected_texts


@pytest.mark.parametrize("xml_path", [None, ".//p"])
def test_partition_xml_keeps_the_text_around_a_comment_or_processing_instruction(
    xml_path: str | None,
):
    xml_text = "<root><p>alpha <!-- a note -->beta</p><p>gamma <?php echo 1; ?>delta</p></root>"

    elements = partition_xml(text=xml_text, xml_path=xml_path)

    assert [e.text for e in elements] == ["alpha beta", "gamma delta"]


class _TrickleFile(io.RawIOBase):
    """A file whose reads return at most `size` bytes, so text is split across parser reads."""

    def __init__(self, data: bytes, size: int):
        self._data, self._position, self._size = data, 0, size
        self.bytes_read = 0

    def readable(self) -> bool:
        return True

    def read(self, size: int | None = -1) -> bytes:
        size = self._size if size is None or size < 0 else min(size, self._size)
        chunk = self._data[self._position : self._position + size]
        self._position += len(chunk)
        self.bytes_read += len(chunk)
        return chunk


@pytest.mark.parametrize("read_size", [1, 2, 3, 7])
def test_partition_xml_does_not_depend_on_where_the_parser_reads_end(read_size: int):
    xml = (
        "<doc><body>Intro <b>bold</b> and caf&#233; &amp; more.<record><name>Alice</name>"
        "<price>12</price></record><!-- c -->tail text<?pi x?> end.</body></doc>"
    ).encode()

    texts = list(get_leaf_elements(None, _TrickleFile(xml, read_size), None, None))

    assert texts == ["Intro bold and café & more.", "Alice", "12", "tail text end."]


def _whitespace_records(count: int) -> bytes:
    return ("<root>" + "<record>   </record>\n" * count + "</root>").encode()


def _records(count: int) -> bytes:
    record = "<record><name>Alice</name><price>12</price></record>\n"
    return ("<root>" + record * count + "</root>").encode()


def _nested_records(depth: int) -> bytes:
    level = "<section>" + "<record><name>Alice</name><price>12</price></record>" * 50
    return (level * depth + "</section>" * depth).encode()


def _peak_memory_while_partitioning(xml: bytes) -> int:
    tracemalloc.start()
    try:
        for _ in get_leaf_elements(None, io.BytesIO(xml), None, None):
            pass
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


@pytest.mark.parametrize(
    ("make_xml", "small", "large"),
    [
        (_whitespace_records, 10_000, 100_000),
        (_records, 10_000, 100_000),
        (_nested_records, 20, 200),
    ],
)
def test_partition_xml_keeps_pending_text_bounded(
    make_xml: Callable[[int], bytes], small: int, large: int
):
    # -- text that is final is emitted, not kept until the root closes, so ten times the input
    # -- does not take ten times the memory --
    small_peak = _peak_memory_while_partitioning(make_xml(small))
    large_peak = _peak_memory_while_partitioning(make_xml(large))

    assert large_peak < 2 * small_peak


def test_partition_xml_streams_the_texts_of_a_large_file():
    xml = _records(100_000)
    file = _TrickleFile(xml, 64 * 1024)

    first_text = next(get_leaf_elements(None, file, None, None))

    assert first_text == "Alice"
    assert file.bytes_read < len(xml) // 10


def test_add_chunking_strategy_on_partition_xml():
    file_path = example_doc_path("factbook.xml")
    elements = partition_xml(file_path)
    chunk_elements = partition_xml(file_path, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_xml_element_metadata_has_languages():
    file_path = example_doc_path("factbook.xml")
    elements = partition_xml(file_path)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_xml_respects_detect_language_per_element():
    elements = partition_xml(
        example_doc_path("language-docs/eng_spa_mult.xml"), detect_language_per_element=True
    )
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
