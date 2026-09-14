"""Test-suite for `unstructured.partition.json` module."""

from __future__ import annotations

import io
import json
import os
import pathlib
import tempfile

import pytest
from pytest_mock import MockFixture

from test_unstructured.unit_utils import example_doc_path
from unstructured.chunking.dispatch import reconstruct_table_from_chunks
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    CompositeElement,
    ElementMetadata,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.file_utils.filetype import detect_filetype
from unstructured.file_utils.model import FileType
from unstructured.partition.email import partition_email
from unstructured.partition.html import partition_html
from unstructured.partition.json import partition_json
from unstructured.partition.text import partition_text
from unstructured.partition.xml import partition_xml
from unstructured.staging.base import elements_to_json

DIRECTORY = pathlib.Path(__file__).parent.resolve()

is_in_docker = os.path.exists("/.dockerenv")

test_files = [
    "fake-text.txt",
    "fake-html.html",
    "eml/fake-email.eml",
]

is_in_docker = os.path.exists("/.dockerenv")


def test_it_chunks_elements_when_a_chunking_strategy_is_specified():
    chunks = partition_json(
        "example-docs/spring-weather.html.json", chunking_strategy="basic", max_characters=1500
    )

    assert len(chunks) == 9
    assert all(isinstance(ch, CompositeElement) for ch in chunks)


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_filename(filename: str):
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
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        test_elements = partition_json(filename=test_path)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0

    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_filename_with_metadata_filename(filename: str):
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
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        test_elements = partition_json(filename=test_path, metadata_filename="test")

    assert len(test_elements) > 0
    assert len(str(test_elements[0])) > 0
    assert all(element.metadata.filename == "test" for element in test_elements)


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_file(filename: str):
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
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path, "rb") as f:
            test_elements = partition_json(file=f)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_file_with_metadata_filename(filename: str):
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
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path, "rb") as f:
            test_elements = partition_json(file=f, metadata_filename="test")

    for i in range(len(test_elements)):
        assert test_elements[i].metadata.filename == "test"


@pytest.mark.parametrize("filename", test_files)
def test_partition_json_from_text(filename: str):
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
        test_path = os.path.join(tmpdir, _filename + ".json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path) as f:
            text = f.read()
        test_elements = partition_json(text=text)

    assert len(elements) > 0
    assert len(str(elements[0])) > 0
    assert len(elements) == len(test_elements)
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
        assert elements[i].metadata.filename == filename.split("/")[-1]


def test_partition_json_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_json()


def test_partition_json_works_with_empty_string():
    assert partition_json(text="") == []


def test_partition_json_works_with_a_whitespace_only_file():
    # -- the file= route reaches the in-body empty-document guard (text="" is caught earlier) --
    assert partition_json(file=io.BytesIO(b"  \n ")) == []


def test_partition_json_emits_Text_element_for_an_empty_object():
    # -- an empty object is a (trivial) document: one Text containing "{}" --
    assert partition_json(text="{}") == [Text(text="{}")]


def test_partition_json_works_with_empty_list():
    assert partition_json(text="[]") == []


def test_partition_json_raises_with_too_many_specified():
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
        test_path = os.path.join(tmpdir, "fake-text.txt.json")
        elements_to_json(elements, filename=test_path, indent=2)
        with open(test_path, "rb") as f:
            text = f.read().decode("utf-8")

    with pytest.raises(ValueError):
        partition_json(filename=test_path, file=f)

    with pytest.raises(ValueError):
        partition_json(filename=test_path, text=text)

    with pytest.raises(ValueError):
        partition_json(file=f, text=text)

    with pytest.raises(ValueError):
        partition_json(filename=test_path, file=f, text=text)


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_json_from_file_path_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.json.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_json(example_doc_path("spring-weather.html.json"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_json_from_file_gets_last_modified_None():
    with open("example-docs/spring-weather.html.json", "rb") as f:
        elements = partition_json(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_json_from_text_gets_last_modified_None():
    with open("example-docs/spring-weather.html.json") as f:
        text = f.read()

    elements = partition_json(text=text)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_json_from_file_path_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.json.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_json(
        "example-docs/spring-weather.html.json", metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_json_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("spring-weather.html.json"), "rb") as f:
        elements = partition_json(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_json_from_text_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open("example-docs/spring-weather.html.json") as f:
        text = f.read()

    elements = partition_json(text=text, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_json_raises_with_invalid_json():
    text = '[{"hi": "there"}]]'
    with pytest.raises(ValueError):
        partition_json(text=text)


# -- arbitrary (non-element-schema) JSON ---------------------------------------------------------


def it_partitions_an_arbitrary_object_into_a_single_Text_element():
    elements = partition_json(text='{"make": "Fabrikam", "model": "F-100"}')

    assert elements == [Text(text='{\n  "make": "Fabrikam",\n  "model": "F-100"\n}')]


def and_it_preserves_deeply_nested_values_in_the_pretty_printed_text():
    text = '{"site": {"address": {"city": "Springfield"}}}'

    elements = partition_json(text=text)

    assert len(elements) == 1
    assert "Springfield" in elements[0].text


def it_partitions_an_array_of_objects_into_one_Text_element_per_object_in_order():
    text = '[{"sku": "A-100"}, {"sku": "B-200"}]'

    elements = partition_json(text=text)

    assert elements == [Text(text='{\n  "sku": "A-100"\n}'), Text(text='{\n  "sku": "B-200"\n}')]


def and_it_partitions_an_arbitrary_array_file_from_disk():
    elements = partition_json(example_doc_path("arbitrary-records.json"))

    assert len(elements) == 3
    assert all(isinstance(e, Text) for e in elements)
    assert "Watering Can" in elements[1].text


def it_partitions_an_array_of_scalars_into_a_single_Text_element():
    elements = partition_json(text="[1, 2, 3]")

    assert elements == [Text(text="[\n  1,\n  2,\n  3\n]")]


def and_it_partitions_a_mixed_type_array_into_a_single_Text_element():
    elements = partition_json(text='[{"a": 1}, 2]')

    assert elements == [Text(text='[\n  {\n    "a": 1\n  },\n  2\n]')]


def it_partitions_a_top_level_scalar_into_a_single_Text_element():
    elements = partition_json(text='"hello"')

    assert elements == [Text(text='"hello"')]


def it_rehydrates_an_element_shaped_array_rather_than_partitioning_it():
    # -- documented limitation: an array of customer records that happens to match the
    # -- serialized-element schema is indistinguishable from Unstructured output, so it
    # -- rehydrates as elements rather than partitioning as arbitrary JSON --
    elements = partition_json(text='[{"type": "Title", "text": "x"}]')

    assert elements == [Title(text="x")]


def but_it_partitions_an_element_typed_object_with_no_text_field_as_Text():
    # -- the other side of the limitation: a recognized element "type" without a "text" field
    # -- cannot rehydrate, so the payload falls through and partitions as arbitrary JSON --
    elements = partition_json(text='[{"type": "Title"}]')

    assert len(elements) == 1
    assert isinstance(elements[0], Text)
    assert '"type": "Title"' in elements[0].text


def it_chunks_an_arbitrary_payload_when_a_chunking_strategy_is_specified():
    chunks = partition_json(text='{"hi": "there"}', chunking_strategy="basic")

    assert len(chunks) == 1
    assert all(isinstance(chunk, CompositeElement) for chunk in chunks)


# -- serialized chunked-table output (TableChunk) round-trip -------------------------------------


def it_round_trips_serialized_chunked_table_output_including_TableChunks():
    # -- completes PR #4291: `reconstruct_table_from_chunks()` expects deserialized chunks, so
    # -- serialized chunker output must round-trip its TableChunk elements rather than silently
    # -- drop them --
    rows = [(f"Item {i}", f"Description of item number {i}") for i in range(1, 25)]
    table_text = "\n".join(f"{name} {desc}" for name, desc in rows)
    table_html = (
        "<table>"
        + "".join(f"<tr><td>{name}</td><td>{desc}</td></tr>" for name, desc in rows)
        + "</table>"
    )
    chunks = chunk_by_title(
        [Title("Inventory"), Table(table_text, metadata=ElementMetadata(text_as_html=table_html))],
        max_characters=500,
        include_orig_elements=True,
    )
    assert sum(isinstance(c, TableChunk) for c in chunks) >= 2
    # -- serialized chunker output in the wild carries `filetype` from its partition run; stamp
    # -- the value partition_json() itself stamps so re-serialization compares byte-for-byte --
    for chunk in chunks:
        chunk.metadata.filetype = "application/json"
    json_text = elements_to_json(chunks)
    assert json_text is not None

    # -- unique_element_ids=True keeps the chunker-assigned ids; hash-id reassignment (#3365)
    # -- is orthogonal to what this test pins --
    elements = partition_json(text=json_text, unique_element_ids=True)

    assert [type(e) for e in elements] == [type(c) for c in chunks]
    assert elements == chunks
    assert elements_to_json(elements) == json_text
    # -- and the rehydrated chunks feed the PR #4291 reconstruction helper --
    [table] = reconstruct_table_from_chunks(elements)
    assert table.text.split() == table_text.split()


# -- element-shaped payload discrimination -------------------------------------------------------


@pytest.mark.parametrize(
    "metadata",
    [
        # -- coordinates points without a coordinate-system --
        {"coordinates": {"points": [[0, 0], [1, 1]]}},
        # -- orig_elements that is not valid base64 --
        {"orig_elements": "not-base64!!"},
        # -- orig_elements that is valid base64 but not gzip-compressed element JSON --
        {"orig_elements": "aGVsbG8="},
    ],
)
def it_raises_ValueError_when_an_element_shaped_payload_has_corrupt_metadata(metadata: dict):
    # -- an element-shaped payload that cannot rehydrate raises loudly, never leaking low-level
    # -- exceptions like `zlib.error` or `binascii.Error` --
    text = json.dumps([{"type": "Title", "text": "x", "metadata": metadata}])

    with pytest.raises(ValueError, match="could not be reconstructed"):
        partition_json(text=text)


def it_partitions_a_non_element_dict_with_a_metadata_key_as_Text():
    # -- a "metadata" key on a non-element-shaped object must not trigger metadata parsing --
    value = {"id": 1, "metadata": {"coordinates": {"points": [[0, 0], [1, 1]]}}}

    elements = partition_json(text=json.dumps([value]))

    assert len(elements) == 1
    assert isinstance(elements[0], Text)
    assert '"id": 1' in elements[0].text
    assert '"coordinates"' in elements[0].text


def it_partitions_a_mixed_array_whole_with_no_partial_rehydration():
    # -- an array mixing element-shaped and arbitrary items partitions whole as arbitrary JSON;
    # -- no partial rehydration that silently drops the arbitrary items --
    text = '[{"type": "Title", "text": "x"}, {"foo": "bar"}]'

    elements = partition_json(text=text)

    assert len(elements) == 2
    assert all(isinstance(e, Text) for e in elements)
    assert '"type": "Title"' in elements[0].text
    assert '"foo": "bar"' in elements[1].text


def it_partitions_an_element_typed_object_with_non_str_text_as_Text():
    elements = partition_json(text='[{"type": "Title", "text": 42}]')

    assert len(elements) == 1
    assert isinstance(elements[0], Text)
    assert '"text": 42' in elements[0].text


def and_it_partitions_an_element_shaped_object_with_non_dict_metadata_as_Text():
    elements = partition_json(text='[{"type": "Title", "text": "x", "metadata": "weird"}]')

    assert len(elements) == 1
    assert isinstance(elements[0], Text)
    assert '"metadata": "weird"' in elements[0].text


def and_it_partitions_an_object_with_an_unhashable_type_value_as_Text():
    # -- `type` holding a non-str (here unhashable) value must not crash the shape predicate --
    elements = partition_json(text='[{"type": ["Title"], "text": "x"}]')

    assert len(elements) == 1
    assert isinstance(elements[0], Text)
    assert '"Title"' in elements[0].text


def it_raises_ValueError_on_a_deeply_nested_payload_rather_than_RecursionError():
    with pytest.raises(ValueError, match="Not a valid json"):
        partition_json(text="[" * 200000)


@pytest.mark.parametrize(
    "payload",
    ["NaN", "Infinity", "-Infinity", '{"x": NaN}', "[1, Infinity, 3]"],
)
def it_rejects_non_standard_json_constants(payload: str):
    # -- NaN/Infinity are accepted by json.loads by default but are not valid JSON --
    with pytest.raises(ValueError, match="Not a valid json"):
        partition_json(text=payload)


def and_it_raises_ValueError_when_a_valid_payload_is_too_deep_to_pretty_print():
    # -- json.loads() (C scanner) parses deeper than json.dumps() (pure Python) can serialize,
    # -- so a valid payload can still fail pretty-printing; that surfaces as ValueError too --
    text = "[" * 5000 + "1" + "]" * 5000

    with pytest.raises(ValueError, match="nested too deeply"):
        partition_json(text=text)


# -- file= routing --------------------------------------------------------------------------------


def it_partitions_an_arbitrary_object_from_a_file_like_object():
    file = io.BytesIO(b'{"make": "Fabrikam", "model": "F-100"}')

    elements = partition_json(file=file)

    assert len(elements) == 1
    assert isinstance(elements[0], Text)
    assert '"make": "Fabrikam"' in elements[0].text


def and_it_raises_ValueError_for_corrupt_element_shaped_metadata_from_a_file_like_object():
    payload = json.dumps(
        [{"type": "Title", "text": "x", "metadata": {"orig_elements": "aGVsbG8="}}]
    ).encode()

    with pytest.raises(ValueError, match="could not be reconstructed"):
        partition_json(file=io.BytesIO(payload))


def it_rehydrates_on_a_detect_then_partition_sequence_over_the_same_file_handle():
    # -- JSON/NDJSON disambiguation restores the file to read position 0, so a follow-up
    # -- partition of the same handle reads the full payload --
    with open(example_doc_path("simple.json"), "rb") as f:
        file = io.BytesIO(f.read())

    assert detect_filetype(file=file) == FileType.JSON

    elements = partition_json(file=file)

    assert elements[0] == Title(text="These are a few of my favorite things:")
