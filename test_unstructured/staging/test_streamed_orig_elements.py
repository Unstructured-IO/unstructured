"""Compression must preserve existing transport bytes and avoid collection-wide copies."""

import base64
import copy
import json
import weakref
import zlib

import pytest

from unstructured.documents.elements import (
    DataSourceMetadata,
    ElementMetadata,
    Image,
    NarrativeText,
)
from unstructured.staging import base


@pytest.mark.parametrize(
    "value",
    [
        {},
        [],
        [True, None, 1, -2.5, float("inf"), float("nan")],
        {1: "integer", 2: "two"},
        {False: "false", True: "true"},
        {None: "null"},
        {"z": ['\\"\n\t\x00', "é🙂\ud800"], "a": "🙂" * 70000},
    ],
)
def test_fragmented_json_is_byte_identical_to_the_sorted_standard_encoder(value):
    assert "".join(base._iter_json_fragments(value)) == json.dumps(value, sort_keys=True)


def test_json_without_large_strings_is_encoded_in_one_fragment():
    value = {"b": [1, 2.5, None], "a": {"c": "text"}}
    assert list(base._iter_json_fragments(value)) == [json.dumps(value, sort_keys=True)]


def test_json_fragments_stay_bounded_around_large_strings():
    value = {
        "metadata": {"image_base64": "x" * 300000, "page_number": 1},
        "record_locator": {"k" * 300000: 1},
        "text": "small",
    }
    fragments = list(base._iter_json_fragments(value))
    assert "".join(fragments) == json.dumps(value, sort_keys=True)
    assert max(len(fragment) for fragment in fragments) <= 65536


@pytest.mark.parametrize("count", [0, 1, 30])
def test_streaming_compression_preserves_existing_bytes_and_input_metadata(count):
    elements = [
        Image(
            text=f"image {index}",
            element_id=f"image-{index}",
            metadata=ElementMetadata(
                image_base64=('é🙂\\"\n' * 20000),
                detection_class_prob=0.123456789,
                languages=["eng"],
            ),
        )
        for index in range(count)
    ]
    before = copy.deepcopy(elements)
    adjusted = base._fix_metadata_field_precision(elements)
    expected = base64.b64encode(
        zlib.compress(json.dumps(base.elements_to_dicts(adjusted), sort_keys=True).encode("utf-8"))
    ).decode("utf-8")
    assert base.elements_to_base64_gzipped_json(iter(elements)) == expected
    assert [element.to_dict() for element in elements] == [element.to_dict() for element in before]


@pytest.mark.parametrize("field", ["extra", "enrichment_origins"])
@pytest.mark.parametrize("container_type", ["dict", "list", "tuple"])
@pytest.mark.parametrize("large_string", [False, True])
def test_compression_preserves_standard_encoder_circular_reference_error(
    field, container_type, large_string
):
    # Put a large string before the back-reference so the scan short-circuits and emission
    # must detect the cycle itself. Without it, the scan must detect the cycle.
    first = "x" * 70000 if large_string else "small"
    if container_type == "dict":
        cyclic = {"a": first}
        cyclic["self"] = cyclic
    else:
        items = [first]
        cyclic = tuple(items + [items]) if container_type == "tuple" else items
        items.append(cyclic)
    metadata = ElementMetadata()
    setattr(metadata, field, cyclic)
    element = NarrativeText("text", element_id="id", metadata=metadata)

    adjusted = base._fix_metadata_field_precision([element])
    with pytest.raises(ValueError, match="^Circular reference detected$") as expected:
        json.dumps(base.elements_to_dicts(adjusted), sort_keys=True)
    with pytest.raises(type(expected.value), match="^Circular reference detected$"):
        base.elements_to_base64_gzipped_json([element])


@pytest.mark.parametrize("large_string", [False, True])
def test_compression_accepts_shared_noncyclic_containers(large_string):
    shared = {"values": ["x" * 70000 if large_string else "small"]}
    metadata = ElementMetadata()
    metadata.extra = {"first": shared, "second": shared, "tuple": (shared, shared)}
    element = NarrativeText("text", element_id="id", metadata=metadata)
    adjusted = base._fix_metadata_field_precision([element])
    expected = base64.b64encode(
        zlib.compress(json.dumps(base.elements_to_dicts(adjusted), sort_keys=True).encode("utf-8"))
    ).decode("ascii")

    assert base.elements_to_base64_gzipped_json([element]) == expected


def test_compression_does_not_retain_consumed_original_elements():
    references = []

    def images():
        for index in range(100):
            element = Image(text=str(index), metadata=ElementMetadata(image_base64="x" * 10000))
            references.append(weakref.ref(element))
            assert sum(reference() is not None for reference in references) <= 2
            yield element

    encoded = base.elements_to_base64_gzipped_json(images())
    assert len(base.elements_from_base64_gzipped_json(encoded)) == 100
    assert all(reference() is None for reference in references)


def test_serializing_chunk_metadata_does_not_deepcopy_its_original_element_graph(monkeypatch):
    original = NarrativeText("original")
    metadata = ElementMetadata(orig_elements=[original])
    real_deepcopy = copy.deepcopy

    def checked_deepcopy(value, *args, **kwargs):
        if isinstance(value, dict):
            assert value.get("orig_elements") is None
        return real_deepcopy(value, *args, **kwargs)

    monkeypatch.setattr(copy, "deepcopy", checked_deepcopy)
    assert (
        base.elements_from_base64_gzipped_json(metadata.to_dict()["orig_elements"])[0].text
        == "original"
    )
    assert metadata.orig_elements[0] is original


@pytest.mark.parametrize("empty", [False, True])
def test_metadata_json_preserves_original_and_continuation_field_order(empty):
    metadata = ElementMetadata(
        filename="document.pdf",
        orig_elements=[] if empty else [NarrativeText("original", element_id="original")],
    )
    metadata.is_continuation = True
    # Nonempty originals keep their insertion position. Empty originals are serialized last
    # because empty list fields are omitted before the serialized originals are added.
    assert list(metadata.to_dict()) == (
        ["filename", "is_continuation", "orig_elements"]
        if empty
        else ["filename", "orig_elements", "is_continuation"]
    )


def test_incompressible_originals_roll_compressed_spool_to_disk(monkeypatch):
    import random
    from contextlib import contextmanager

    real_spool = base.tempfile.SpooledTemporaryFile
    rolled = []

    @contextmanager
    def tracked_spool(*args, **kwargs):
        with real_spool(*args, **kwargs) as spool:
            yield spool
            rolled.append(spool._rolled)

    monkeypatch.setattr(base.tempfile, "SpooledTemporaryFile", tracked_spool)
    payload = base64.b64encode(random.Random(4517).randbytes(2 * 1024 * 1024)).decode()
    original = Image(
        text="image", element_id="image", metadata=ElementMetadata(image_base64=payload)
    )
    encoded = base.elements_to_base64_gzipped_json([original])
    assert rolled == [True]
    assert base.elements_from_base64_gzipped_json(encoded)[0].to_dict() == original.to_dict()


@pytest.mark.parametrize(
    ("leaf", "depth"), [("small", 600), ("x" * 70000, 1100)], ids=["small-leaf", "large-leaf"]
)
def test_compression_accepts_metadata_nested_as_deeply_as_the_standard_encoder_does(leaf, depth):
    nested = leaf
    for _ in range(depth):
        nested = [nested]
    metadata = ElementMetadata(data_source=DataSourceMetadata(record_locator={"extra": nested}))
    element = NarrativeText("text", element_id="id", metadata=metadata)

    adjusted = base._fix_metadata_field_precision([element])
    expected = base64.b64encode(
        zlib.compress(json.dumps(base.elements_to_dicts(adjusted), sort_keys=True).encode("utf-8"))
    ).decode("utf-8")
    assert base.elements_to_base64_gzipped_json([element]) == expected
