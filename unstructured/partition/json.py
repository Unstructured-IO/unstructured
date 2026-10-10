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

from unstructured.chunking.dispatch import chunk
from unstructured.documents.elements import Element, assign_and_map_hash_ids
from unstructured.file_utils.filetype import FileType
from unstructured.partition.common.common import add_element_metadata, exactly_one
from unstructured.partition.common.json_partitioning import (
    elements_from_arbitrary_value,
    is_element_shaped_dict,
    loads_strict_json,
    rehydrate_elements,
)
from unstructured.partition.common.metadata import get_last_modified_date, set_element_hierarchy
from unstructured.telemetry import partition_runtime_telemetry


def _apply_chunking(
    elements: list[Element],
    *,
    filename: Optional[str],
    file: Optional[IO[bytes]],
    text: Optional[str],
    metadata_last_modified: Optional[str],
    kwargs: dict[str, Any],
) -> list[Element]:
    """Apply the requested chunking strategy before final metadata processing."""
    call_args = {
        "filename": filename,
        "file": file,
        "text": text,
        "metadata_last_modified": metadata_last_modified,
        **kwargs,
    }
    chunking_strategy = call_args.pop("chunking_strategy", None)
    if chunking_strategy is None:
        return elements

    return chunk(elements, chunking_strategy, **call_args)


@partition_runtime_telemetry("json")
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
      elements.
    - Arbitrary JSON: any other valid JSON value is converted to `Text` elements containing the
      pretty-printed JSON. An object or a top-level scalar yields one `Text`; an array of objects
      yields one `Text` per object; any other array (scalars or mixed types) yields a single
      `Text` containing the whole array. An empty object yields one `Text` containing "{}";
      an empty array yields no elements.

    An empty or whitespace-only document yields no elements. The mode is chosen by a shape
    predicate: a non-empty array whose every item looks like a serialized element (recognized
    `type` with its required field of the right type, and a dict `metadata` when present)
    rehydrates; anything else partitions as arbitrary JSON, including an array mixing
    element-shaped and arbitrary items (no partial rehydration). An element-shaped payload whose
    contents cannot be rehydrated (e.g. corrupt `metadata`) raises `ValueError`. Limitation: a
    customer array whose items all happen to look like serialized elements (e.g.
    `{"type": "Title", "text": ...}`) rehydrates instead of being treated as arbitrary JSON.

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
    if not (text is not None and not text.strip() and not file and not filename):
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

    try:
        value = loads_strict_json(file_text) if file_text.strip() else []
    except (json.JSONDecodeError, RecursionError):
        raise ValueError("Not a valid json")

    is_rehydration = (
        isinstance(value, list) and bool(value) and all(is_element_shaped_dict(i) for i in value)
    )
    elements = rehydrate_elements(value) if is_rehydration else elements_from_arbitrary_value(value)

    if is_rehydration:
        if metadata_last_modified:
            for element in elements:
                element.metadata.last_modified = metadata_last_modified
        elements = _apply_chunking(
            elements,
            filename=filename,
            file=file,
            text=text,
            metadata_last_modified=metadata_last_modified,
            kwargs=kwargs,
        )
        metadata_filename = kwargs.get("metadata_filename")
        for element in elements:
            if element.metadata.attached_to_filename is None:
                add_element_metadata(
                    element,
                    filename=metadata_filename,
                    url=kwargs.get("url"),
                    text_as_html=kwargs.get("text_as_html"),
                )
            if metadata_last_modified:
                element.metadata.last_modified = metadata_last_modified

        if (
            kwargs.get("chunking_strategy") is not None
            and kwargs.get("unique_element_ids", False) is False
        ):
            elements = assign_and_map_hash_ids(elements)
    else:
        for element in elements:
            element.metadata.last_modified = metadata_last_modified or last_modified

        elements = _apply_chunking(
            elements,
            filename=filename,
            file=file,
            text=text,
            metadata_last_modified=metadata_last_modified,
            kwargs=kwargs,
        )
        elements = set_element_hierarchy(elements)
        metadata_filename = kwargs.get("metadata_filename") or filename
        for element in elements:
            if element.metadata.attached_to_filename is None:
                add_element_metadata(
                    element,
                    filename=metadata_filename,
                    filetype=FileType.JSON.mime_type,
                    url=kwargs.get("url"),
                    text_as_html=kwargs.get("text_as_html"),
                )

        if kwargs.get("unique_element_ids", False) is False:
            elements = assign_and_map_hash_ids(elements)

    return elements
