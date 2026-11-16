"""Check ownership of data-source fields in serialized element metadata."""

from __future__ import annotations

import copy

import pytest

from unstructured.documents.elements import DataSourceMetadata, ElementMetadata, Text
from unstructured.staging.base import elements_to_dicts


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
