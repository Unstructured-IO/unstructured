"""Provides `partition_json()`.

Partitions any valid JSON document. Serialized Unstructured output (a JSON array of
element-dicts) is "rehydrated" back into its constituent elements, essentially the same function
as `elements_from_json()`; this allows a document of already-partitioned elements to be combined
transparently with other documents in a partitioning run and allows multiple (low-cost) chunking
runs to be performed on a document while only incurring partitioning cost once. Any other valid
JSON (arbitrary customer schemas) is converted to `Text` elements containing the pretty-printed
JSON.
"""

from __future__ import annotations

import json
from typing import IO, Any, Optional

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, Text, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common.common import exactly_one
from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.staging.base import elements_from_dicts


@process_metadata()
@add_metadata_with_filetype(FileType.JSON)
@add_chunking_strategy
def partition_json(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    **kwargs: Any,
) -> list[Element]:
    """Partitions a JSON document into its constituent elements.

    Operates in two modes:

    - Rehydration: a JSON array of serialized Unstructured elements is converted back into those
      elements, exactly as before.
    - Arbitrary JSON: any other valid JSON value is converted to `Text` elements containing the
      pretty-printed JSON. An object or a top-level scalar yields one `Text`; an array of objects
      yields one `Text` per object; any other array (scalars or mixed types) yields a single
      `Text` containing the whole array. An empty object or array yields no elements.

    The mode is chosen by whether `elements_from_dicts()` yields at least one element for a list
    payload. Known v1 limitations: a customer array whose items happen to look like serialized
    elements (e.g. `{"type": "Title", "text": ...}`) rehydrates instead of being treated as
    arbitrary JSON, and an array mixing element-shaped and arbitrary items may partially
    rehydrate, dropping the arbitrary items.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    text
        The string representation of the .json document.
    metadata_last_modified
        The last modified date for the document.
    """
    if text is not None and text.strip() == "" and not file and not filename:
        return []

    exactly_one(filename=filename, file=file, text=text)

    last_modified = get_last_modified_date(filename) if filename else None
    file_text = ""
    if filename is not None:
        with open(filename, encoding="utf8") as f:
            file_text = f.read()

    elif file is not None:
        file_content = file.read()
        file_text = file_content if isinstance(file_content, str) else file_content.decode()
        file.seek(0)

    elif text is not None:
        file_text = str(text)

    if not file_text.strip():
        return []

    try:
        value = json.loads(file_text)
    except json.JSONDecodeError:
        raise ValueError("Not a valid json")

    elements: list[Element] = []
    if isinstance(value, list) and value:
        try:
            # -- Branch A: rehydrate serialized Unstructured elements --
            elements = elements_from_dicts(value)
        except (KeyError, AttributeError, TypeError):
            # -- arbitrary JSON that only superficially resembles serialized elements --
            elements = []
    if not elements:
        # -- Branch B: arbitrary JSON --
        elements = _elements_from_arbitrary_json(value)

    for element in elements:
        element.metadata.last_modified = metadata_last_modified or last_modified

    return elements


def _elements_from_arbitrary_json(value: Any) -> list[Element]:
    """Convert an arbitrary (non element-schema) JSON value to `Text` elements.

    v1 flat contract: each element's text is the pretty-printed JSON of the whole value, or of
    each object when the value is an all-object array. No per-field metadata and no JSONPath
    addressing. This function is the single swap-point for a future structure-aware walker.
    """
    # NOTE(json-partitioning): sort_keys=True per PRD for stable output; alphabetizes customer
    # field order — revisit if source-order fidelity is required.
    if isinstance(value, dict):
        return [Text(text=json.dumps(value, indent=2, sort_keys=True))] if value else []
    if isinstance(value, list):
        if not value:
            return []
        if all(isinstance(item, dict) for item in value):
            return [Text(text=json.dumps(item, indent=2, sort_keys=True)) for item in value]
        return [Text(text=json.dumps(value, indent=2, sort_keys=True))]
    # -- scalar (str / number / bool / null) --
    return [Text(text=json.dumps(value))]
