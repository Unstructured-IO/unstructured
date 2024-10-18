from __future__ import annotations

from typing import IO, Any, Optional

import pandas as pd

from unstructured.chunking import add_chunking_strategy
from unstructured.common.html_table import HtmlTable
from unstructured.documents.elements import Element, ElementMetadata, Table
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import (
    exactly_one,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date

DETECTION_ORIGIN: str = "tsv"


@apply_metadata(FileType.TSV)
@add_chunking_strategy
def partition_tsv(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    include_header: bool = False,
    **kwargs: Any,
) -> list[Element]:
    """Partitions TSV files into document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_header
        Determines whether or not header info info is included in text and medatada.text_as_html.
    """
    exactly_one(filename=filename, file=file)

    header = 0 if include_header else None

    if filename:
        dataframe = pd.read_csv(filename, sep="\t", header=header)
    else:
        assert file is not None
        # -- Note(scanny): `SpooledTemporaryFile` on Python<3.11 does not implement `.readable()`
        # -- which triggers an exception on `pd.DataFrame.read_csv()` call.
        f = spooled_to_bytes_io_if_needed(file)
        dataframe = pd.read_csv(f, sep="\t", header=header)

    html_table = HtmlTable.from_html_text(
        dataframe.to_html(index=False, header=include_header, na_rep="")
    )

    metadata = ElementMetadata(
        filename=filename,
        last_modified=get_last_modified_date(filename) if filename else None,
        text_as_html=html_table.html,
    )
    metadata.detection_origin = DETECTION_ORIGIN

    return [Table(text=html_table.text, metadata=metadata)]
