"""Empty coordinate metadata remains serializable through public exporters."""

import json

import pytest

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import CoordinatesMetadata, ElementMetadata, Text
from unstructured.staging.base import (
    elements_from_base64_gzipped_json,
    elements_to_base64_gzipped_json,
    elements_to_dicts,
    elements_to_json,
    elements_to_ndjson,
)


@pytest.mark.parametrize("route", ["dict", "json", "ndjson", "compressed"])
@pytest.mark.parametrize("probability", [None, 0.1234567])
def test_empty_coordinate_metadata_survives_export(route, probability):
    coordinates = CoordinatesMetadata(points=None, system=None)
    element = Text(
        "Text without a location",
        element_id="source",
        metadata=ElementMetadata(coordinates=coordinates, detection_class_prob=probability),
    )
    original = coordinates.to_dict()

    if route == "dict":
        exported = elements_to_dicts([element])[0]
    elif route == "json":
        exported = json.loads(elements_to_json([element]))[0]
    elif route == "ndjson":
        exported = json.loads(elements_to_ndjson([element]))
    else:
        restored = elements_from_base64_gzipped_json(elements_to_base64_gzipped_json([element]))[0]
        exported = restored.to_dict()

    assert exported["element_id"] == "source"
    assert exported["metadata"]["coordinates"] == original
    if probability is not None:
        assert exported["metadata"]["detection_class_prob"] == (
            probability if route == "dict" else 0.12346
        )
    assert element.metadata.coordinates is coordinates
    assert coordinates.to_dict() == original
    assert element.metadata.detection_class_prob == probability


def test_populated_coordinates_are_still_rounded_without_mutating_source():
    coordinates = CoordinatesMetadata(
        points=((1.234, 5.678), (9.876, 2.345)),
        system=PixelSpace(width=100, height=200),
    )
    element = Text("Located text", metadata=ElementMetadata(coordinates=coordinates))

    exported = json.loads(elements_to_json([element]))[0]

    assert exported["metadata"]["coordinates"]["points"] == [[1.2, 5.7], [9.9, 2.3]]
    assert coordinates.points == ((1.234, 5.678), (9.876, 2.345))


def test_absent_coordinate_metadata_keeps_its_export_shape():
    assert "coordinates" not in elements_to_dicts([Text("Unlocated")])[0]["metadata"]
