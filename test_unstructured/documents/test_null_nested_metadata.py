import json
import zlib
from copy import deepcopy
from io import BytesIO

import pytest

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import (
    CoordinatesMetadata,
    DataSourceMetadata,
    ElementMetadata,
    NarrativeText,
    Text,
)
from unstructured.partition.json import partition_json
from unstructured.partition.ndjson import partition_ndjson
from unstructured.staging.base import elements_from_dicts

NESTED_FIELDS = ("coordinates", "data_source", "orig_elements", "key_value_pairs")


def make_record(metadata):
    return {
        "type": "NarrativeText",
        "element_id": "paragraph-1",
        "text": "The source paragraph is retained.",
        "metadata": metadata,
    }


@pytest.mark.parametrize("field", NESTED_FIELDS)
@pytest.mark.parametrize("loader", ["dicts", "json", "ndjson"])
def test_null_nested_fields_rehydrate_as_absent_fields(field, loader):
    record = make_record({field: None, "filename": "report.pdf", "page_number": 2})
    before = deepcopy(record)

    if loader == "dicts":
        (element,) = elements_from_dicts([record])
    elif loader == "json":
        (element,) = partition_json(text=json.dumps([record]))
    else:
        (element,) = partition_ndjson(text=json.dumps(record))

    assert isinstance(element, NarrativeText)
    assert element.text == record["text"]
    assert getattr(element.metadata, field) is None
    assert field not in element.metadata.to_dict()
    assert element.metadata.filename == "report.pdf"
    assert element.metadata.page_number == 2
    assert record == before


def test_direct_metadata_deserialization_handles_all_null_fields_together():
    source = dict.fromkeys((*NESTED_FIELDS, "filename", "custom_field"))

    metadata = ElementMetadata.from_dict(source)

    assert metadata.to_dict() == {}
    assert all(getattr(metadata, field) is None for field in NESTED_FIELDS)
    assert not hasattr(metadata, "custom_field")
    assert source == dict.fromkeys((*NESTED_FIELDS, "filename", "custom_field"))


@pytest.mark.parametrize(
    ("partitioner", "format_name"), [(partition_json, "json"), (partition_ndjson, "ndjson")]
)
@pytest.mark.parametrize("input_kind", ["filename", "file"])
def test_file_inputs_accept_null_nested_metadata(partitioner, format_name, input_kind, tmp_path):
    record = make_record(dict.fromkeys(NESTED_FIELDS))
    payload = json.dumps([record] if format_name == "json" else record).encode("utf-8")
    if input_kind == "filename":
        path = tmp_path / ("document." + format_name)
        path.write_bytes(payload)
        kwargs = {"filename": str(path)}
    else:
        kwargs = {"file": BytesIO(payload)}

    (element,) = partitioner(**kwargs)

    assert element.text == record["text"]
    assert all(getattr(element.metadata, field) is None for field in NESTED_FIELDS)


@pytest.mark.parametrize("null_field", NESTED_FIELDS)
def test_null_fields_do_not_interfere_with_populated_nested_siblings(null_field):
    populated = ElementMetadata(
        coordinates=CoordinatesMetadata(points=((1.0, 2.0), (3.0, 4.0)), system=PixelSpace(10, 20)),
        data_source=DataSourceMetadata(
            url="https://example.com/document", record_locator={"id": 4}
        ),
        orig_elements=[Text("Original paragraph", element_id="original")],
    )
    populated.key_value_pairs = [
        {
            "key": {
                "text": "Name",
                "layout_element_id": "label",
                "custom_element": Text("Name", element_id="key"),
            },
            "value": {
                "text": "Ada",
                "layout_element_id": "value",
                "custom_element": Text("Ada", element_id="value"),
            },
            "confidence": 0.9,
        }
    ]
    source = populated.to_dict()
    source[null_field] = None
    before = deepcopy(source)

    metadata = ElementMetadata.from_dict(source)

    assert getattr(metadata, null_field) is None
    assert metadata.to_dict() == {k: v for k, v in source.items() if v is not None}
    assert source == before


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("coordinates", 42, AttributeError),
        ("data_source", 42, AttributeError),
        ("orig_elements", "!", zlib.error),
        ("key_value_pairs", [{}], KeyError),
    ],
)
def test_non_null_malformed_nested_values_still_raise(field, value, error):
    with pytest.raises(error):
        ElementMetadata.from_dict({field: value})


def test_other_falsey_values_keep_their_existing_meaning():
    source = {"page_number": 0, "is_continuation": False, "filename": "", "custom_count": 0}

    metadata = ElementMetadata.from_dict(source)

    assert metadata.to_dict() == source
