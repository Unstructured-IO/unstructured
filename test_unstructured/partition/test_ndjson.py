"""Test-suite for `unstructured.partition.ndjson` module."""

from __future__ import annotations

import io
import json
import os
import pathlib
import tempfile

import pytest
from pytest_mock import MockFixture

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.elements import CompositeElement, TableChunk, Text, Title
from unstructured.file_utils.model import FileType
from unstructured.partition.email import partition_email
from unstructured.partition.html import partition_html
from unstructured.partition.ndjson import partition_ndjson
from unstructured.partition.text import partition_text
from unstructured.partition.xml import partition_xml
from unstructured.staging.base import elements_to_ndjson

DIRECTORY = pathlib.Path(__file__).parent.resolve()

is_in_docker = os.path.exists("/.dockerenv")

test_files = [
    "fake-text.txt",
    "fake-html.html",
    "eml/fake-email.eml",
]

is_in_docker = os.path.exists("/.dockerenv")


def test_it_chunks_elements_when_a_chunking_strategy_is_specified():
    chunks = partition_ndjson(
        example_doc_path("spring-weather.html.ndjson"),
        chunking_strategy="basic",
        max_characters=1500,
    )

    assert len(chunks) == 9
    assert all(isinstance(ch, CompositeElement) for ch in chunks)


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_filename(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        test_elements = partition_ndjson(filename=test_path)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0

    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_filename_with_metadata_filename(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        test_elements = partition_ndjson(filename=test_path, metadata_filename="test")

    assert len(test_elements) > 0
    assert len(str(test_elements[0])) > 0
    assert all(element.metadata.filename == "test" for element in test_elements)


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_file(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        with open(test_path, "rb") as f:
            test_elements = partition_ndjson(file=f)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_file_with_metadata_filename(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)
    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        with open(test_path, "rb") as f:
            test_elements = partition_ndjson(file=f, metadata_filename="test")

    for i in range(len(test_elements)):
        assert test_elements[i].metadata.filename == "test"


@pytest.mark.parametrize("filename", test_files)
def test_partition_ndjson_from_text(filename: str):
    path = example_doc_path(filename)
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        _filename = os.path.basename(filename)
        test_path = os.path.join(tmpdir, _filename + ".ndjson")
        elements_to_ndjson(elements, filename=test_path)
        with open(test_path) as f:
            text = f.read()
        test_elements = partition_ndjson(text=text)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


def test_partition_ndjson_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_ndjson()


def test_partition_ndjson_works_with_empty_string():
    assert partition_ndjson(text="") == []


def test_partition_ndjson_works_with_a_blank_lines_only_file():
    # -- the file= route reaches the no-parsed-values guard (text="" is caught earlier) --
    assert partition_ndjson(file=io.BytesIO(b"\n  \n")) == []


def test_partition_ndjson_emits_Text_element_for_an_empty_object_line():
    # -- arbitrary NDJSON yields one `Text` element per line, even when the line is `{}` --
    assert partition_ndjson(text="{}") == [Text(text="{}")]


def test_partition_ndjson_emits_Text_element_for_an_empty_array_line():
    assert partition_ndjson(text="[]") == [Text(text="[]")]


def test_partition_ndjson_raises_with_too_many_specified():
    path = example_doc_path("fake-text.txt")
    elements = []
    filetype = FileType.from_extension(os.path.splitext(path)[1])
    if filetype == FileType.TXT:
        elements = partition_text(filename=path)
    if filetype == FileType.HTML:
        elements = partition_html(filename=path)
    if filetype == FileType.XML:
        elements = partition_xml(filename=path)
    if filetype == FileType.EML:
        elements = partition_email(filename=path)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "fake-text.txt.ndjson")
        elements_to_ndjson(elements, filename=test_path)
        with open(test_path, "rb") as f:
            text = f.read().decode("utf-8")

    with pytest.raises(ValueError):
        partition_ndjson(filename=test_path, file=f)

    with pytest.raises(ValueError):
        partition_ndjson(filename=test_path, text=text)

    with pytest.raises(ValueError):
        partition_ndjson(file=f, text=text)

    with pytest.raises(ValueError):
        partition_ndjson(filename=test_path, file=f, text=text)


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_ndjson_from_file_path_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.ndjson.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    elements = partition_ndjson(example_doc_path("spring-weather.html.ndjson"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_ndjson_from_file_gets_last_modified_None():
    with open(example_doc_path("spring-weather.html.ndjson"), "rb") as f:
        elements = partition_ndjson(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_ndjson_from_text_gets_last_modified_None():
    with open(example_doc_path("spring-weather.html.ndjson")) as f:
        text = f.read()

    elements = partition_ndjson(text=text)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_ndjson_from_file_path_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.ndjson.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    elements = partition_ndjson(
        example_doc_path("spring-weather.html.ndjson"),
        metadata_last_modified=metadata_last_modified,
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_ndjson_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("spring-weather.html.ndjson"), "rb") as f:
        elements = partition_ndjson(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_ndjson_from_text_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("spring-weather.html.ndjson")) as f:
        text = f.read()

    elements = partition_ndjson(text=text, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_ndjson_raises_with_invalid_json():
    text = '[{"hi": "there"}]]'
    with pytest.raises(ValueError):
        partition_ndjson(text=text)


# -- arbitrary (non-element-schema) NDJSON -------------------------------------------------------


def it_partitions_arbitrary_ndjson_into_one_Text_element_per_line_in_line_order():
    text = '{"sku": "A-100", "qty": 3}\n{"sku": "B-200", "qty": 1}\n{"sku": "C-300", "qty": 7}\n'

    elements = partition_ndjson(text=text)

    assert elements == [
        Text(text='{\n  "qty": 3,\n  "sku": "A-100"\n}'),
        Text(text='{\n  "qty": 1,\n  "sku": "B-200"\n}'),
        Text(text='{\n  "qty": 7,\n  "sku": "C-300"\n}'),
    ]


def and_it_keeps_an_array_valued_line_as_a_single_Text_element():
    # -- one `Text` per line even when the line is an array; NDJSON mode never explodes a line
    # -- into one element per array item the way JSON mode does for an all-object array --
    elements = partition_ndjson(text='[{"a": 1}, {"b": 2}]\n')

    assert elements == [Text(text='[\n  {\n    "a": 1\n  },\n  {\n    "b": 2\n  }\n]')]


def and_it_skips_blank_lines():
    text = '{"sku": "A-100"}\n\n   \n{"sku": "B-200"}\n'

    elements = partition_ndjson(text=text)

    assert len(elements) == 2
    assert all(isinstance(e, Text) for e in elements)
    assert '"sku": "A-100"' in elements[0].text
    assert '"sku": "B-200"' in elements[1].text


def and_it_partitions_an_arbitrary_ndjson_file_from_disk():
    elements = partition_ndjson(example_doc_path("arbitrary-records.ndjson"))

    assert len(elements) == 3
    assert all(isinstance(e, Text) for e in elements)
    assert "Watering Can" in elements[1].text


def it_still_raises_when_the_file_contains_a_malformed_line():
    text = '{"sku": "A-100"}\nnot-json\n{"sku": "B-200"}\n'

    with pytest.raises(ValueError):
        partition_ndjson(text=text)


def it_still_rehydrates_serialized_element_ndjson_rather_than_partitioning_it():
    elements = partition_ndjson(example_doc_path("simple.ndjson"))

    assert elements[0] == Title(text="These are a few of my favorite things:")


def and_it_rehydrates_element_shaped_lines_including_a_TableChunk_line():
    # -- TableChunk is special-cased (like CheckBox) in both the shape predicate and
    # -- `elements_from_dicts()`, so serialized chunker output rehydrates with classes
    # -- preserved rather than the TableChunk line being silently dropped --
    text = (
        '{"type": "Title", "text": "Regional Sales"}\n'
        '{"type": "TableChunk", "text": "Region Total",'
        ' "metadata": {"table_id": "t-1", "chunk_index": 0}}\n'
    )

    elements = partition_ndjson(text=text)

    assert [type(e) for e in elements] == [Title, TableChunk]
    assert elements[1].text == "Region Total"
    assert elements[1].metadata.table_id == "t-1"


def it_chunks_arbitrary_ndjson_when_a_chunking_strategy_is_specified():
    chunks = partition_ndjson(text='{"hi": "there"}\n', chunking_strategy="basic")

    assert len(chunks) == 1
    assert all(isinstance(chunk, CompositeElement) for chunk in chunks)


# -- element-shaped line discrimination ----------------------------------------------------------


def it_raises_ValueError_when_an_element_shaped_line_has_corrupt_metadata():
    # -- an element-shaped line that cannot rehydrate raises loudly, never leaking low-level
    # -- exceptions like `zlib.error` --
    line = json.dumps({"type": "Title", "text": "x", "metadata": {"orig_elements": "aGVsbG8="}})

    with pytest.raises(ValueError, match="could not be reconstructed"):
        partition_ndjson(text=line + "\n")


def it_partitions_mixed_element_and_arbitrary_lines_all_as_Text_one_per_line():
    # -- a file mixing element-shaped and arbitrary lines partitions whole as arbitrary NDJSON;
    # -- no partial rehydration that silently drops the arbitrary lines --
    text = '{"type": "Title", "text": "x"}\n{"foo": "bar"}\n'

    elements = partition_ndjson(text=text)

    assert len(elements) == 2
    assert all(isinstance(e, Text) for e in elements)
    assert '"type": "Title"' in elements[0].text
    assert '"foo": "bar"' in elements[1].text


def it_partitions_a_line_with_an_unhashable_type_value_as_arbitrary_ndjson():
    # -- `type` holding a non-str (here unhashable) value must not crash the shape predicate --
    elements = partition_ndjson(text='{"type": ["Title"], "text": "x"}\n')

    assert len(elements) == 1
    assert isinstance(elements[0], Text)
    assert '"Title"' in elements[0].text


def it_raises_ValueError_on_a_deeply_nested_line_rather_than_RecursionError():
    with pytest.raises(ValueError, match="Not a valid ndjson"):
        partition_ndjson(text="[" * 200000)


@pytest.mark.parametrize("payload", ["NaN", "Infinity", "-Infinity", '{"x": NaN}'])
def it_rejects_non_standard_json_constants_on_a_line(payload: str):
    # -- a line with NaN/Infinity is not valid JSON, even though json.loads accepts it --
    with pytest.raises(ValueError, match="Not a valid ndjson"):
        partition_ndjson(text=payload + "\n")


def and_it_raises_ValueError_when_a_valid_line_is_too_deep_to_pretty_print():
    # -- json.loads() (C scanner) parses deeper than json.dumps() (pure Python) can serialize,
    # -- so a valid line can still fail pretty-printing; that surfaces as ValueError too --
    text = "[" * 5000 + "1" + "]" * 5000

    with pytest.raises(ValueError, match="nested too deeply"):
        partition_ndjson(text=text)


# -- file= routing --------------------------------------------------------------------------------


def it_partitions_arbitrary_lines_from_a_file_like_object():
    file = io.BytesIO(b'{"sku": "A-100"}\n{"sku": "B-200"}\n')

    elements = partition_ndjson(file=file)

    assert len(elements) == 2
    assert all(isinstance(e, Text) for e in elements)
    assert '"sku": "A-100"' in elements[0].text
    assert '"sku": "B-200"' in elements[1].text
