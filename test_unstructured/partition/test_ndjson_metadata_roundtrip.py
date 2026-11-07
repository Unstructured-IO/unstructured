"""Source timestamps survive serialized-element rehydration unless overridden."""

import pytest

from unstructured.documents.elements import ElementMetadata, Text
from unstructured.partition.ndjson import partition_ndjson
from unstructured.staging.base import elements_to_ndjson


@pytest.mark.parametrize("override", [None, "2026-01-02T03:04:05"])
def test_rehydrated_source_timestamp_survives_without_an_override(override):
    original_time = "2001-02-03T04:05:06"
    original = Text("A source paragraph", metadata=ElementMetadata(last_modified=original_time))
    serialized = elements_to_ndjson([original])
    restored = partition_ndjson(text=serialized, metadata_last_modified=override)
    assert restored[0].text == original.text
    assert restored[0].metadata.last_modified == (override or original_time)


def test_arbitrary_ndjson_accepts_explicit_timestamp():
    timestamp = "2026-01-02T03:04:05"
    result = partition_ndjson(text='{"customer": "value"}', metadata_last_modified=timestamp)
    assert result[0].metadata.last_modified == timestamp
