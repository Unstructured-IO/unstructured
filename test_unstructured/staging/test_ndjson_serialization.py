import json
from copy import deepcopy

import pytest

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import CheckBox, CoordinatesMetadata, ElementMetadata, Text
from unstructured.staging.base import elements_to_ndjson


@pytest.mark.parametrize("as_iterator", [False, True])
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_ndjson_serialization_preserves_values_rounding_and_source(as_iterator, encoding, tmp_path):
    element = Text(
        "café\n東京",
        element_id="text-1",
        metadata=ElementMetadata(
            coordinates=CoordinatesMetadata(
                ((10.123, 20.345), (10.123, 30.456), (40.567, 30.456), (40.567, 20.345)),
                PixelSpace(612, 792),
            ),
            detection_class_prob=0.987654321,
            link_urls=["https://example.com/a", "https://example.com/b"],
            link_texts=["first", "second"],
        ),
    )
    checkbox = CheckBox(checked=True, element_id="checkbox-1")
    elements = [element, checkbox]
    before = deepcopy([item.to_dict() for item in elements])
    output = tmp_path / "elements.ndjson"

    result = elements_to_ndjson(
        iter(elements) if as_iterator else elements, filename=str(output), encoding=encoding
    )

    assert output.read_text(encoding=encoding) == result
    assert not result.endswith("\n")
    serialized = [json.loads(line) for line in result.split("\n")]
    assert [item["element_id"] for item in serialized] == ["text-1", "checkbox-1"]
    assert serialized[0]["text"] == element.text
    assert serialized[0]["metadata"]["coordinates"]["points"] == [
        [10.1, 20.3],
        [10.1, 30.5],
        [40.6, 30.5],
        [40.6, 20.3],
    ]
    assert serialized[0]["metadata"]["detection_class_prob"] == 0.98765
    assert serialized[0]["metadata"]["link_urls"] == element.metadata.link_urls
    assert serialized[1]["type"] == "CheckBox"
    assert serialized[1]["checked"] is True
    assert result == "\n".join(json.dumps(item, sort_keys=True) for item in serialized)
    assert [item.to_dict() for item in elements] == before


def test_empty_element_iterator_serializes_to_an_empty_file(tmp_path):
    output = tmp_path / "empty.ndjson"
    output.write_text("old contents", encoding="utf-8")

    result = elements_to_ndjson(iter(()), filename=str(output))

    assert result == ""
    assert output.read_bytes() == b""
