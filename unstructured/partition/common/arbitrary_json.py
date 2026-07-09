"""Shared helpers for partitioning JSON and NDJSON payloads.

Both `partition_json()` and `partition_ndjson()` choose between two modes -- "rehydrating"
serialized Unstructured elements and partitioning arbitrary customer JSON -- using
`is_serialized_element_dict()` as the discriminator.

A dict counts as element-shaped only when its `type` is recognized AND the type-specific required
field is present with the right type AND `metadata` (when present) is a dict. This mirrors what
`elements_from_dicts()` (unstructured/staging/base.py) actually requires: it parses
`item["metadata"]` before checking `type`, requires `item["text"]` for text types and
`item["checked"]` for CheckBox, and silently skips unrecognized types.

`elements_from_arbitrary_json()` is the swap-point for JSON-mode structure (a future
structure-aware walker would replace it). `pretty_json_text()` is the shared formatter used by
BOTH partitioners; NDJSON keeps its own strict one-`Text`-per-line loop in `partition_ndjson()`
because its `{}` -> `Text("{}")` contract deliberately differs from JSON's `{}` -> no elements.
"""

from __future__ import annotations

import json
from typing import Any

from unstructured.documents.elements import TYPE_TO_TEXT_ELEMENT_MAP, Element, Text
from unstructured.staging.base import elements_from_dicts


def is_serialized_element_dict(item: Any) -> bool:
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
        return "checked" in item
    return False


def rehydrate_elements(values: list[Any]) -> list[Element]:
    """`elements_from_dicts()` with corrupt-payload failures wrapped as `ValueError`.

    A payload that passes `is_serialized_element_dict()` can still fail rehydration on corrupt
    field contents (e.g. malformed `metadata.coordinates` or a non-gzip `metadata.orig_elements`).
    Those failures raise loudly as `ValueError` with the underlying exception chained, rather
    than leaking low-level errors like `zlib.error` or `binascii.Error`.
    """
    try:
        return elements_from_dicts(values)
    except Exception as e:
        raise ValueError(
            "JSON payload is element-shaped but could not be rehydrated as serialized"
            f" Unstructured elements: {e}"
        ) from e


def pretty_json_text(value: Any) -> str:
    """The pretty-printed JSON text used for arbitrary-JSON `Text` elements."""
    # NOTE(json-partitioning): sort_keys=True per PRD for stable output; alphabetizes customer
    # field order — revisit if source-order fidelity is required.
    return json.dumps(value, indent=2, sort_keys=True)


def elements_from_arbitrary_json(value: Any) -> list[Element]:
    """Convert an arbitrary (non element-schema) JSON value to `Text` elements.

    v1 flat contract: each element's text is the pretty-printed JSON of the whole value, or of
    each object when the value is an all-object array. No per-field metadata and no JSONPath
    addressing. This function is the swap-point for a future structure-aware walker.
    """
    if isinstance(value, dict):
        return [Text(text=pretty_json_text(value))] if value else []
    if isinstance(value, list):
        if not value:
            return []
        if all(isinstance(item, dict) for item in value):
            return [Text(text=pretty_json_text(item)) for item in value]
        return [Text(text=pretty_json_text(value))]
    # -- scalar (str / number / bool / null) --
    return [Text(text=pretty_json_text(value))]
