"""Check ownership of data-source fields in serialized element metadata."""

from __future__ import annotations

import base64
import copy
import json
import weakref
import zlib
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from unstructured.documents.elements import DataSourceMetadata, ElementMetadata, Text
from unstructured.staging.base import elements_to_base64_gzipped_json, elements_to_dicts


@pytest.mark.parametrize(
    "serialize",
    [
        DataSourceMetadata.to_dict,
        lambda source: ElementMetadata(data_source=source).to_dict()["data_source"],
        lambda source: Text("paragraph", metadata=ElementMetadata(data_source=source)).to_dict()[
            "metadata"
        ]["data_source"],
        lambda source: elements_to_dicts(
            [Text("paragraph", metadata=ElementMetadata(data_source=source))]
        )[0]["metadata"]["data_source"],
    ],
    ids=["data-source", "metadata", "element", "staging"],
)
@pytest.mark.parametrize("mutate_export", [True, False], ids=["export", "source"])
def test_serialized_data_source_does_not_share_nested_values(serialize, mutate_export):
    source = DataSourceMetadata(
        url="https://example.com/document",
        version="1",
        record_locator={"folder": {"path": ["team", "document"]}},
        permissions_data=[{"members": [{"name": "reader"}]}],
    )
    source_before = copy.deepcopy(source)
    exported = serialize(source)
    export_before = copy.deepcopy(exported)

    if mutate_export:
        exported["record_locator"]["folder"]["path"].append("redacted")
        exported["permissions_data"][0]["members"][0]["name"] = "anonymous"
        assert source == source_before
        assert serialize(source) == export_before
    else:
        source.record_locator["folder"]["path"].append("updated")
        source.permissions_data[0]["members"][0]["name"] = "another reader"
        assert exported == export_before


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (DataSourceMetadata(), {}),
        (
            DataSourceMetadata(record_locator={}, permissions_data=[]),
            {"record_locator": {}, "permissions_data": []},
        ),
        (DataSourceMetadata(url="", version="0"), {"url": "", "version": "0"}),
    ],
)
def test_data_source_serialization_keeps_empty_values_and_field_order(source, expected):
    actual = source.to_dict()
    assert actual == expected
    assert list(actual) == list(expected)


@pytest.mark.parametrize("separate_wrappers", [False, True])
def test_bulk_export_copies_a_shared_source_graph_once(separate_wrappers):
    permissions = [{"members": [{"name": str(i)}]} for i in range(512)]
    locator = {"folder": {"path": ["team", "document"]}}
    source = DataSourceMetadata(record_locator=locator, permissions_data=permissions)
    elements = [
        Text(
            str(i),
            metadata=ElementMetadata(
                data_source=(
                    DataSourceMetadata(record_locator=locator, permissions_data=permissions)
                    if separate_wrappers
                    else source
                )
            ),
        )
        for i in range(64)
    ]

    exported = elements_to_dicts(iter(elements))
    sources = [item["metadata"]["data_source"] for item in exported]

    assert len({id(item) for item in exported}) == 64
    assert len({id(item["metadata"]) for item in exported}) == 64
    assert len({id(item) for item in sources}) == 64
    assert len({id(item["permissions_data"]) for item in sources}) == 1
    assert len({id(item["record_locator"]) for item in sources}) == 1
    assert sources[0]["permissions_data"] == permissions
    assert sources[0]["permissions_data"] is not permissions

    sources[0]["permissions_data"][0]["members"][0]["name"] = "redacted"
    assert sources[1]["permissions_data"][0]["members"][0]["name"] == "redacted"
    assert permissions[0]["members"][0]["name"] == "0"
    locator["folder"]["path"].append("changed source")
    assert sources[0]["record_locator"]["folder"]["path"] == ["team", "document"]
    sources[0]["permissions_data"] = []
    assert len(sources[1]["permissions_data"]) == 512


@pytest.mark.parametrize("bulk", [False, True])
def test_separate_exports_do_not_share_a_detached_source_graph(bulk):
    shared = {"members": ["reader"]}
    source = DataSourceMetadata(record_locator={"entry": shared}, permissions_data=[shared])
    element = Text("paragraph", metadata=ElementMetadata(data_source=source))

    def serialize():
        return (
            elements_to_dicts([element])[0]["metadata"]["data_source"] if bulk else source.to_dict()
        )

    first, second = serialize(), serialize()
    assert first["record_locator"]["entry"] is first["permissions_data"][0]
    assert second["record_locator"]["entry"] is second["permissions_data"][0]
    first["permissions_data"][0]["members"].append("writer")
    assert second["permissions_data"][0]["members"] == ["reader"]
    assert shared["members"] == ["reader"]


@pytest.mark.parametrize(("depth", "leaf"), [(600, "small"), (1100, "x" * 70000)])
@pytest.mark.parametrize("path", ["source", "metadata", "element", "bulk", "orig-elements"])
def test_deep_source_locators_preserve_supported_serialization(depth, leaf, path):
    nested = leaf
    for _ in range(depth):
        nested = [nested]
    source = DataSourceMetadata(record_locator={"extra": nested})
    element = Text("paragraph", element_id="id", metadata=ElementMetadata(data_source=source))
    expected = {
        "type": "UncategorizedText",
        "element_id": "id",
        "text": "paragraph",
        "metadata": {"data_source": {"record_locator": {"extra": nested}}},
    }
    # Establish that this depth is accepted by the pre-copy JSON path on this interpreter.
    expected_json = json.dumps([expected], sort_keys=True)
    if path == "orig-elements":
        encoded = ElementMetadata(orig_elements=[element]).to_dict()["orig_elements"]
        assert zlib.decompress(base64.b64decode(encoded)).decode() == expected_json
        return

    exported = (
        source.to_dict()
        if path == "source"
        else element.metadata.to_dict()["data_source"]
        if path == "metadata"
        else element.to_dict()["metadata"]["data_source"]
        if path == "element"
        else elements_to_dicts([element])[0]["metadata"]["data_source"]
    )
    actual, original = exported["record_locator"]["extra"], nested
    for _ in range(depth):
        assert actual is not original
        actual, original = actual[0], original[0]
    assert actual == original == leaf


def test_nested_bulk_exports_restore_the_outer_copy_scope():
    source = DataSourceMetadata(record_locator={"path": ["source"]})
    nested = []

    class NestedText(Text):
        def to_dict(self):
            result = super().to_dict()
            nested.extend(elements_to_dicts([Text("inner", metadata=self.metadata)]))
            return result

    metadata = ElementMetadata(data_source=source)
    exported = elements_to_dicts(
        [NestedText("first", metadata=metadata), Text("second", metadata=metadata)]
    )
    first = exported[0]["metadata"]["data_source"]["record_locator"]
    second = exported[1]["metadata"]["data_source"]["record_locator"]
    inner = nested[0]["metadata"]["data_source"]["record_locator"]
    assert first is second
    assert inner is not first
    assert inner is not source.record_locator
    assert source.to_dict()["record_locator"] is not first


@pytest.mark.parametrize("nested", [False, True])
def test_failed_bulk_exports_restore_the_previous_copy_scope(nested):
    source = DataSourceMetadata(record_locator={"path": ["source"]})
    metadata = ElementMetadata(data_source=source)
    failed = []

    class FailingText(Text):
        def to_dict(self):
            failed.append(super().to_dict())
            raise ValueError("serialization failed")

    def fail():
        with pytest.raises(ValueError, match="^serialization failed$"):
            elements_to_dicts([FailingText("fail", metadata=metadata)])

    class RecoveringText(Text):
        def to_dict(self):
            result = super().to_dict()
            fail()
            return result

    if nested:
        exported = elements_to_dicts(
            [RecoveringText("first", metadata=metadata), Text("second", metadata=metadata)]
        )
        first = exported[0]["metadata"]["data_source"]["record_locator"]
        assert first is exported[1]["metadata"]["data_source"]["record_locator"]
        assert first is not failed[0]["metadata"]["data_source"]["record_locator"]
    else:
        fail()
    assert (
        source.to_dict()["record_locator"]
        is not failed[0]["metadata"]["data_source"]["record_locator"]
    )


def test_concurrent_bulk_exports_do_not_share_copy_scopes():
    source = DataSourceMetadata(record_locator={"path": ["source"]})
    barrier = Barrier(2)

    class SynchronizedText(Text):
        def to_dict(self):
            barrier.wait(timeout=10)
            return super().to_dict()

    def export(_):
        metadata = ElementMetadata(data_source=source)
        return elements_to_dicts(
            [SynchronizedText("first", metadata=metadata), Text("second", metadata=metadata)]
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = executor.map(export, range(2))
    a = first[0]["metadata"]["data_source"]["record_locator"]
    b = second[0]["metadata"]["data_source"]["record_locator"]
    assert a is first[1]["metadata"]["data_source"]["record_locator"]
    assert b is second[1]["metadata"]["data_source"]["record_locator"]
    assert a is not b
    assert a is not source.record_locator
    assert b is not source.record_locator


def test_bulk_input_iteration_does_not_capture_unrelated_exports():
    source = DataSourceMetadata(record_locator={"path": ["source"]})
    unrelated = []

    def elements():
        for _ in range(2):
            unrelated.append(source.to_dict())
            yield Text("paragraph", metadata=ElementMetadata(data_source=source))

    exported = elements_to_dicts(elements())
    locator = exported[0]["metadata"]["data_source"]["record_locator"]
    assert locator is exported[1]["metadata"]["data_source"]["record_locator"]
    assert unrelated[0]["record_locator"] is not unrelated[1]["record_locator"]
    assert all(item["record_locator"] is not locator for item in unrelated)


def test_streamed_originals_do_not_retain_source_graphs_in_an_outer_bulk_export():
    references = []

    class Permissions(list):
        pass

    def originals():
        for index in range(20):
            permissions = Permissions([{"members": [str(index)]}])
            references.append(weakref.ref(permissions))
            assert sum(reference() is not None for reference in references) <= 2
            yield Text(
                str(index),
                metadata=ElementMetadata(
                    data_source=DataSourceMetadata(permissions_data=permissions)
                ),
            )

    class StreamingText(Text):
        def to_dict(self):
            result = super().to_dict()
            result["compressed"] = elements_to_base64_gzipped_json(originals())
            return result

    exported = elements_to_dicts([StreamingText("outer")])
    assert len(json.loads(zlib.decompress(base64.b64decode(exported[0]["compressed"])))) == 20
    assert all(reference() is None for reference in references)


@pytest.mark.parametrize("container", ["dict", "list", "tuple"])
def test_source_copy_preserves_container_types_aliases_and_cycle_errors(container):
    shared = {"members": ["reader"]}
    if container == "dict":
        value = {"first": shared, "second": shared}
        value["cycle"] = value
    elif container == "list":
        value = [shared, shared]
        value.append(value)
    else:
        items = [shared, shared]
        value = tuple(items + [items])
        items.append(value)
    source = DataSourceMetadata(record_locator={"value": value})
    expected = copy.deepcopy(source.record_locator)
    exported = source.to_dict()["record_locator"]
    assert type(exported["value"]) is type(expected["value"])
    assert exported["value"] is not value
    if container == "dict":
        assert exported["value"]["first"] is exported["value"]["second"]
        assert exported["value"]["cycle"] is exported["value"]
    else:
        assert exported["value"][0] is exported["value"][1]
        cycle = exported["value"][2] if container == "list" else exported["value"][2][2]
        assert cycle is exported["value"]
    with pytest.raises(ValueError, match="^Circular reference detected$"):
        json.dumps(exported)
