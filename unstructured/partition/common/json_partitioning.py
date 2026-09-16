"""Shared helpers for partitioning JSON and NDJSON payloads.

Both `partition_json()` and `partition_ndjson()` choose between two modes -- "rehydrating"
serialized Unstructured elements and partitioning arbitrary customer JSON -- using
`is_element_shaped_dict()` as the discriminator.

A dict counts as element-shaped only when its `type` is recognized AND the type-specific required
field is present with the right type AND `metadata` (when present) is a dict. This mirrors the
shapes `elements_from_dicts()` (unstructured/staging/base.py) actually accepts -- the
`TYPE_TO_TEXT_ELEMENT_MAP` types plus the CheckBox and TableChunk special cases: it parses
`item["metadata"]` before checking `type`, requires `item["text"]` for text types (TableChunk
included) and `item["checked"]` for CheckBox, and silently skips unrecognized types.

`elements_from_arbitrary_value()` is the swap-point for JSON-mode structure (a future
structure-aware walker would replace it). `pretty_json_text()` is the shared formatter used by
BOTH partitioners; NDJSON keeps its own strict one-`Text`-per-line loop in `partition_ndjson()`
because its contract deliberately differs from JSON mode for empty arrays: an `[]` NDJSON line
yields `Text("[]")` whereas an `[]` JSON document yields no elements (both modes emit `Text("{}")`
for an empty object). An NDJSON line that is itself an array also stays one `Text` per line
rather than exploding into one element per array item.

`loads_strict_json()` is the shared parser both partitioners use so that non-standard JSON
constants (`NaN`, `Infinity`, `-Infinity`), which `json.loads` accepts by default, are rejected
as malformed rather than partitioned. It lives in the low-level `unstructured.utils` module (so
`file_utils.filetype` can share it without an import cycle) and is re-exported here for the
callers that already import it from this module.
"""

from __future__ import annotations

import json
from typing import IO, Any, Optional

from unstructured.documents.elements import TYPE_TO_TEXT_ELEMENT_MAP, Element, Text
from unstructured.staging.base import elements_from_dicts
from unstructured.utils import loads_strict_json as loads_strict_json


def _decode_bytes(data: bytes, encoding: Optional[str]) -> str:
    """Decode `data`, honoring an explicit `encoding` and preserving valid UTF-8 otherwise.

    An explicit `encoding` is authoritative: it is used as-is so a caller who knows the codec
    always gets it, and a genuine mismatch surfaces as an error rather than mojibake.

    With no `encoding`, UTF-8 is tried first. Charset detection is only a fallback for bytes that
    are not valid UTF-8, because a detector can report high confidence in a legacy codec for a
    byte sequence that is also valid UTF-8 -- decoding it that way would silently corrupt text
    that JSON still parses successfully.
    """
    if encoding is not None:
        from unstructured.file_utils.encoding import format_encoding_str

        return data.decode(format_encoding_str(encoding))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        from unstructured.file_utils.encoding import detect_file_encoding

        _, decoded = detect_file_encoding(file=data)
        return decoded


def read_json_text(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    encoding: Optional[str] = None,
) -> str:
    """Read JSON/NDJSON source text from `filename` or an open `file`.

    The file-like contract is the one callers already rely on: the object is read once from its
    current position, an already-decoded `str` is passed through untouched, and the stream is
    never reopened or taken ownership of.
    """
    if filename is not None:
        with open(filename, "rb") as f:
            return _decode_bytes(f.read(), encoding)

    assert file is not None
    file_content = file.read()
    if isinstance(file_content, str):
        return file_content
    return _decode_bytes(file_content, encoding)


def is_element_shaped_dict(item: Any) -> bool:
    """True when `item` plausibly represents one serialized Unstructured element."""
    if not isinstance(item, dict):
        return False
    metadata = item.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        return False
    item_type = item.get("type")
    # -- recognized types are all strings; a non-str (possibly unhashable) value is customer data --
    if not isinstance(item_type, str):
        return False
    if item_type in TYPE_TO_TEXT_ELEMENT_MAP:
        return isinstance(item.get("text"), str)
    if item_type == "CheckBox":
        return isinstance(item.get("checked"), bool)
    if item_type == "TableChunk":
        return isinstance(item.get("text"), str)
    return False


def rehydrate_elements(values: list[dict[str, Any]]) -> list[Element]:
    """`elements_from_dicts()` with corrupt-payload failures wrapped as `ValueError`.

    A payload that passes `is_element_shaped_dict()` can still fail rehydration on corrupt
    field contents (e.g. malformed `metadata.coordinates` or a non-gzip `metadata.orig_elements`).
    Those failures raise loudly as `ValueError` with the underlying exception chained, rather
    than leaking low-level errors like `zlib.error` or `binascii.Error`.
    """
    try:
        return elements_from_dicts(values)
    except Exception as e:
        raise ValueError(
            "Payload resembles serialized Unstructured elements but could not be"
            f" reconstructed: {e}"
        ) from e


def pretty_json_text(value: Any) -> str:
    """The pretty-printed JSON text used for arbitrary-JSON `Text` elements."""
    # NOTE(simon): sort_keys=True gives deterministic, diffable output; it alphabetizes
    # customer field order -- revisit if source-order fidelity is required.
    try:
        return json.dumps(value, indent=2, sort_keys=True)
    except RecursionError:
        raise ValueError("JSON value is nested too deeply to partition")


def elements_from_arbitrary_value(value: Any) -> list[Element]:
    """Convert an arbitrary (non element-shaped) JSON value to `Text` elements.

    Current flat contract: each element's text is the pretty-printed JSON of the whole value, or
    of each object when the value is an all-object array. No per-field metadata and no JSONPath
    addressing. This function is the swap-point for a future structure-aware walker.
    """
    if isinstance(value, dict):
        # -- an empty object yields one Text containing "{}" (an empty array yields nothing) --
        return [Text(text=pretty_json_text(value))]
    if isinstance(value, list):
        if not value:
            return []
        if all(isinstance(item, dict) for item in value):
            return [Text(text=pretty_json_text(item)) for item in value]
        return [Text(text=pretty_json_text(value))]
    # -- scalar (str / number / bool / null) --
    return [Text(text=pretty_json_text(value))]
