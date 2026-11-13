"""Large-record reconstruction retains serialization and error contracts."""

import base64
import json
import os
import tracemalloc
import zlib

import pytest

from unstructured.errors import DecompressedSizeExceededError
from unstructured.staging import base


def _encoded(raw):
    return base64.b64encode(zlib.compress(raw)).decode()


@pytest.mark.parametrize("text", ["ASCII", "é日本語", "𝄞😀🧪", '\x00\n\\"'])
def test_decode_preserves_unicode_payload_metadata_and_order(text):
    originals = [{"type": "NarrativeText", "element_id": "original", "text": "nested"}]
    nested = _encoded(json.dumps(originals).encode())
    record = {
        "type": "Image",
        "element_id": "image",
        "text": text,
        "metadata": {
            "page_number": 9,
            "image_base64": "AAECAwQ=",
            "image_mime_type": "image/bmp",
            "filename": "日本語.bmp",
            "languages": ["jpn", "eng"],
            "orig_elements": nested,
            "coordinates": {
                "points": [[0.25, 1.5], [0.25, 5.5], [8.25, 5.5], [8.25, 1.5]],
                "system": "PixelSpace",
                "layout_width": 10,
                "layout_height": 6,
            },
        },
    }
    second = {"type": "NarrativeText", "element_id": "second", "text": "second"}
    encoded = _encoded(json.dumps([record, second], ensure_ascii=False).encode())
    elements = base.elements_from_base64_gzipped_json(encoded)
    expected = base.elements_from_dicts([record, second])
    assert json.dumps([element.to_dict() for element in elements]) == json.dumps(
        [element.to_dict() for element in expected]
    )
    assert [element.id for element in elements] == ["image", "second"]
    assert elements[0].metadata.orig_elements[0].text == "nested"


@pytest.mark.parametrize("extra", [b"", b"ignored trailing compressed stream"])
def test_decode_keeps_existing_trailing_data_behavior(extra):
    encoded = base64.b64encode(zlib.compress(b"[]") + extra).decode()
    assert base.elements_from_base64_gzipped_json(encoded) == []


@pytest.mark.parametrize(
    ("raw", "error"), [(b"\xff", UnicodeDecodeError), (b"{", json.JSONDecodeError)]
)
def test_decode_keeps_utf8_and_json_errors(raw, error):
    with pytest.raises(error):
        base.elements_from_base64_gzipped_json(_encoded(raw))


def test_decode_keeps_corrupt_or_incomplete_compression_errors():
    compressed = zlib.compress(b"[]")
    with pytest.raises(zlib.error, match="Incomplete or corrupted compressed data"):
        base.elements_from_base64_gzipped_json(base64.b64encode(compressed[:-1]).decode())
    with pytest.raises(zlib.error):
        base.elements_from_base64_gzipped_json(base64.b64encode(b"invalid").decode())


def test_decode_keeps_existing_size_cap_at_exact_boundary(monkeypatch):
    raw = json.dumps([{"type": "NarrativeText", "text": "A" * 1000}]).encode()
    encoded = _encoded(raw)
    monkeypatch.setattr(base, "MAX_DECOMPRESSED_SIZE", len(raw))
    assert base.elements_from_base64_gzipped_json(encoded)[0].text == "A" * 1000
    monkeypatch.setattr(base, "MAX_DECOMPRESSED_SIZE", len(raw) - 1)
    with pytest.raises(DecompressedSizeExceededError):
        base.elements_from_base64_gzipped_json(encoded)


def test_decode_releases_each_consumed_buffer_before_the_next_stage(monkeypatch):
    # -- Base64 text of random bytes stays large after compression, so a retained compressed
    # -- buffer is as visible as a retained decompressed one.
    text = base64.b64encode(os.urandom(6 * 1024 * 1024)).decode()
    size = len(text)
    encoded = _encoded(json.dumps([{"type": "NarrativeText", "text": text}]).encode())
    live_at_entry = {}

    def traced(name, stage):
        def wrapper(value):
            live_at_entry[name] = tracemalloc.get_traced_memory()[0] - baseline
            return stage(value)

        return wrapper

    monkeypatch.setattr(base.json, "loads", traced("json.loads", json.loads))
    monkeypatch.setattr(
        base, "elements_from_dicts", traced("elements_from_dicts", base.elements_from_dicts)
    )
    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()
    try:
        baseline = tracemalloc.get_traced_memory()[0]
        elements = base.elements_from_base64_gzipped_json(encoded)
    finally:
        if not was_tracing:
            tracemalloc.stop()
    assert elements[0].text == text
    # -- each stage starts with only its own input alive: the JSON text, then the parsed dicts --
    assert live_at_entry["json.loads"] < 1.5 * size
    assert live_at_entry["elements_from_dicts"] < 1.5 * size
