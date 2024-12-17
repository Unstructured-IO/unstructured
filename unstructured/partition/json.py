"""Provides `partition_json()`.

Note this does not partition arbitrary JSON. Its only use-case is to "rehydrate" unstructured
document elements serialized to JSON, essentially the same function as `elements_from_json()`, but
this allows a document of already-partitioned elements to be combined transparently with other
documents in a partitioning run. It also allows multiple (low-cost) chunking runs to be performed on
a document while only incurring partitioning cost once.
"""

from __future__ import annotations

import json
from typing import IO, Any, Optional

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import (
    FileType,
    add_metadata_with_filetype,
    is_json_processable,
)
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
    """Partitions serialized Unstructured output into its constituent elements.

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

    if not is_json_processable(file_text=file_text):
        raise ValueError(
            "JSON cannot be partitioned. Schema does not match the Unstructured schema.",
        )

    try:
        element_dicts = json.loads(file_text)
        elements = elements_from_dicts(element_dicts)
    except json.JSONDecodeError:
        raise ValueError("Not a valid json")

    for element in elements:
        element.metadata.last_modified = metadata_last_modified or last_modified

    return elements
