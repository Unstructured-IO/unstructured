"""Test-suite for `unstructured.partition.json` module."""

from __future__ import annotations

import json
import os
import pathlib
import tempfile

import pytest
from pytest_mock import MockFixture

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.elements import CompositeElement, Text, Title
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


def test_partition_json_works_with_empty_object():
    # -- an empty object yields no elements, mirroring the empty-list behavior --
    assert partition_json(text="{}") == []


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


def test_partition_json_emits_Text_elements_for_non_element_json_array():
    # -- an array that does not conform to the Unstructured element schema partitions as
    # -- arbitrary JSON, one `Text` element per object --
    text = '[{"invalid": "schema"}]'

    elements = partition_json(text=text)

    assert elements == [Text(text='{\n  "invalid": "schema"\n}')]


def test_partition_json_emits_Text_element_for_non_element_json_object():
    # -- an object is not a list of element-dicts, so it partitions as arbitrary JSON --
    text = '{"hi": "there"}'

    elements = partition_json(text=text)

    assert elements == [Text(text='{\n  "hi": "there"\n}')]


def test_partition_json_raises_with_invalid_json():
    text = '[{"hi": "there"}]]'
    with pytest.raises(ValueError):
        partition_json(text=text)


# -- arbitrary (non-element-schema) JSON ---------------------------------------------------------


def it_partitions_an_arbitrary_json_object_into_a_single_Text_element():
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


def and_it_partitions_an_arbitrary_json_array_file_from_disk():
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


def it_rehydrates_an_element_shaped_array_instead_of_treating_it_as_arbitrary_json():
    # -- documented v1 limitation: an array of customer records that happens to match the
    # -- serialized-element schema is indistinguishable from Unstructured output, so it
    # -- rehydrates as elements rather than partitioning as arbitrary JSON --
    elements = partition_json(text='[{"type": "Title", "text": "x"}]')

    assert elements == [Title(text="x")]


def but_it_partitions_an_element_typed_object_with_no_text_field_as_arbitrary_json():
    # -- the other side of the limitation: a recognized element "type" without a "text" field
    # -- cannot rehydrate, so the payload falls through and partitions as arbitrary JSON --
    elements = partition_json(text='[{"type": "Title"}]')

    assert elements == [Text(text='{\n  "type": "Title"\n}')]


def it_chunks_arbitrary_json_when_a_chunking_strategy_is_specified():
    chunks = partition_json(text='{"hi": "there"}', chunking_strategy="basic")

    assert len(chunks) == 1
    assert all(isinstance(chunk, CompositeElement) for chunk in chunks)


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

    with pytest.raises(ValueError, match="could not be rehydrated"):
        partition_json(text=text)


def it_partitions_a_non_element_dict_with_a_metadata_key_as_arbitrary_json():
    # -- a "metadata" key on a non-element-shaped object must not trigger metadata parsing --
    value = {"id": 1, "metadata": {"coordinates": {"points": [[0, 0], [1, 1]]}}}

    elements = partition_json(text=json.dumps([value]))

    assert elements == [Text(text=json.dumps(value, indent=2, sort_keys=True))]


def it_partitions_a_mixed_array_whole_as_arbitrary_json():
    # -- an array mixing element-shaped and arbitrary items partitions whole as arbitrary JSON;
    # -- no partial rehydration that silently drops the arbitrary items --
    text = '[{"type": "Title", "text": "x"}, {"foo": "bar"}]'

    elements = partition_json(text=text)

    assert elements == [
        Text(text='{\n  "text": "x",\n  "type": "Title"\n}'),
        Text(text='{\n  "foo": "bar"\n}'),
    ]


def it_partitions_an_element_typed_object_with_non_str_text_as_arbitrary_json():
    elements = partition_json(text='[{"type": "Title", "text": 42}]')

    assert elements == [Text(text='{\n  "text": 42,\n  "type": "Title"\n}')]


def it_partitions_an_element_shaped_object_with_non_dict_metadata_as_arbitrary_json():
    elements = partition_json(text='[{"type": "Title", "text": "x", "metadata": "weird"}]')

    assert elements == [
        Text(text='{\n  "metadata": "weird",\n  "text": "x",\n  "type": "Title"\n}'),
    ]


def and_it_partitions_an_object_with_an_unhashable_type_value_as_arbitrary_json():
    # -- `type` holding a non-str (here unhashable) value must not crash the shape predicate --
    elements = partition_json(text='[{"type": ["Title"], "text": "x"}]')

    assert elements == [Text(text='{\n  "text": "x",\n  "type": [\n    "Title"\n  ]\n}')]


def it_raises_ValueError_on_a_deeply_nested_payload_rather_than_RecursionError():
    with pytest.raises(ValueError, match="Not a valid json"):
        partition_json(text="[" * 200000)
