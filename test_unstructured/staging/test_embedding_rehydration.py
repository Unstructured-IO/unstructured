"""Serialized vectors survive element rehydration and public round trips."""

import json

import pytest

from unstructured.documents.elements import (
    TYPE_TO_TEXT_ELEMENT_MAP,
    CheckBox,
    CompositeElement,
    ElementMetadata,
    TableChunk,
    Text,
)
from unstructured.partition.json import partition_json
from unstructured.partition.ndjson import partition_ndjson
from unstructured.staging.base import (
    elements_from_base64_gzipped_json,
    elements_from_dicts,
    elements_from_json,
    elements_to_base64_gzipped_json,
    elements_to_dicts,
    elements_to_json,
    elements_to_ndjson,
)


@pytest.mark.parametrize("element_type", [*TYPE_TO_TEXT_ELEMENT_MAP, "TableChunk"])
def test_rehydration_retains_vectors_for_every_text_type(element_type):
    payload = {
        "type": element_type,
        "element_id": "source-element",
        "text": "A cached embedding",
        "embeddings": [0.25, -0.5, 0.0],
        "metadata": {"filename": "document.txt", "page_number": 2},
    }

    element = elements_from_dicts([payload])[0]

    assert element.embeddings == payload["embeddings"]
    assert element.id == "source-element"
    assert element.metadata.filename == "document.txt"
    assert element.metadata.page_number == 2


@pytest.mark.parametrize("embeddings", [None, []])
def test_direct_rehydration_preserves_null_and_empty_vectors(embeddings):
    element = elements_from_dicts(
        [{"type": "NarrativeText", "text": "text", "embeddings": embeddings}]
    )[0]

    assert element.embeddings == embeddings


def test_missing_vector_and_checkbox_keep_existing_behavior():
    elements = elements_from_dicts(
        [
            {"type": "NarrativeText", "text": "text"},
            {"type": "CheckBox", "checked": True},
        ]
    )

    assert elements[0].embeddings is None
    assert isinstance(elements[1], CheckBox)
    assert elements[1].checked is True


@pytest.mark.parametrize("route", ["dict", "json", "compressed", "partition_json", "ndjson"])
def test_public_round_trip_retains_vectors(route):
    original = [
        Text("first", element_id="a", embeddings=[1.0, 0.0, -0.25]),
        TableChunk("second", element_id="b", embeddings=[0.0, 1.0, 0.5]),
    ]

    if route == "dict":
        restored = elements_from_dicts(elements_to_dicts(original))
    elif route == "json":
        restored = elements_from_json(text=elements_to_json(original))
    elif route == "compressed":
        restored = elements_from_base64_gzipped_json(elements_to_base64_gzipped_json(original))
    elif route == "partition_json":
        restored = partition_json(text=elements_to_json(original))
    else:
        restored = partition_ndjson(text=elements_to_ndjson(original), unique_element_ids=True)

    assert [e.embeddings for e in restored] == [e.embeddings for e in original]
    assert [e.text for e in restored] == ["first", "second"]


def test_compressed_original_elements_retain_their_vectors():
    original = Text("source", element_id="source", embeddings=[0.125, -0.75])
    chunk = CompositeElement("source", metadata=ElementMetadata(orig_elements=[original]))

    restored = elements_from_json(text=elements_to_json([chunk]))[0]

    assert restored.metadata.orig_elements[0].embeddings == [0.125, -0.75]
    assert json.loads(elements_to_json([original]))[0]["embeddings"] == [0.125, -0.75]
