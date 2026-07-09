"""Provides `partition_ndjson()`.

Partitions any valid NDJSON document. Serialized Unstructured output (one element-dict per line)
is "rehydrated" back into its constituent elements, essentially the same function as
`elements_from_json()`; this allows a document of already-partitioned elements to be combined
transparently with other documents in a partitioning run and allows multiple (low-cost) chunking
runs to be performed on a document while only incurring partitioning cost once. Any other valid
NDJSON (arbitrary customer records) is converted to `Text` elements containing the pretty-printed
JSON, one per line.
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
@add_metadata_with_filetype(FileType.NDJSON)
@add_chunking_strategy
def partition_ndjson(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    **kwargs: Any,
) -> list[Element]:
    """Partitions an NDJSON document into its constituent elements.

    Operates in two modes:

    - Rehydration: lines of serialized Unstructured elements are converted back into those
      elements, exactly as before.
    - Arbitrary NDJSON: any other valid NDJSON becomes one `Text` element per line, containing
      the pretty-printed JSON of that line's value.

    Blank lines are skipped; a file that is empty or all-blank yields no elements. The mode is
    chosen by whether `elements_from_dicts()` yields at least one element for the parsed lines.
    Known v1 limitations: customer lines that happen to look like serialized elements (e.g.
    `{"type": "Title", "text": ...}`) rehydrate instead of being treated as arbitrary NDJSON,
    and a file mixing element-shaped and arbitrary lines may partially rehydrate, dropping the
    arbitrary lines.

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

    values: list[Any] = []
    try:
        for line in file_text.splitlines():
            if not line.strip():
                continue
            values.append(json.loads(line))
    except json.JSONDecodeError:
        raise ValueError("Not a valid ndjson")

    if not values:
        return []

    elements: list[Element] = []
    if all(isinstance(value, dict) for value in values):
        try:
            # -- Branch A: rehydrate serialized Unstructured elements --
            elements = elements_from_dicts(values)
        except (KeyError, AttributeError, TypeError):
            # -- arbitrary NDJSON that only superficially resembles serialized elements --
            elements = []
    if not elements:
        # -- Branch B: arbitrary NDJSON, one Text element per line value --
        # NOTE(json-partitioning): sort_keys=True per PRD for stable output; alphabetizes
        # customer field order — revisit if source-order fidelity is required.
        elements = [Text(text=json.dumps(value, indent=2, sort_keys=True)) for value in values]

    for element in elements:
        element.metadata.last_modified = metadata_last_modified or last_modified

    return elements
