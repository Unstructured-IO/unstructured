from __future__ import annotations

from typing import IO, Any, Optional

import pandas as pd
from lxml.html.soupparser import fromstring as soupparser_fromstring

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    Table,
    process_metadata,
)
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.lang import apply_lang_metadata

DETECTION_ORIGIN: str = "tsv"


@process_metadata()
@add_metadata_with_filetype(FileType.TSV)
@add_chunking_strategy
def partition_tsv(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    include_header: bool = False,
    include_metadata: bool = True,
    languages: Optional[list[str]] = ["auto"],
    # NOTE (jennings) partition_tsv generates a single TableElement
    # so detect_language_per_element is not included as a param
    date_from_file_object: bool = False,
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
    include_metadata
        Determines whether or not metadata is included in the output.
    metadata_last_modified
        The day of the last modification.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True, attempt
        infer last_modified metadata from bytes, otherwise set it to None.
    """
    exactly_one(filename=filename, file=file)

    last_modification_date = None
    header = 0 if include_header else None

    if filename:
        table = pd.read_csv(filename, sep="\t", header=header)
        last_modification_date = get_last_modified_date(filename)
    elif file:
        # -- Note(scanny): `SpooledTemporaryFile` on Python<3.11 does not implement `.readable()`
        # -- which triggers an exception on `pd.DataFrame.read_csv()` call.
        f = spooled_to_bytes_io_if_needed(file)
        table = pd.read_csv(f, sep="\t", header=header)
        last_modification_date = (
            get_last_modified_date_from_file(file) if date_from_file_object else None
        )

    html_text = table.to_html(index=False, header=include_header, na_rep="")
    text = soupparser_fromstring(html_text).text_content()

    if include_metadata:
        metadata = ElementMetadata(
            text_as_html=html_text,
            filename=metadata_filename or filename,
            last_modified=metadata_last_modified or last_modification_date,
            languages=languages,
        )
        metadata.detection_origin = DETECTION_ORIGIN
    else:
        metadata = ElementMetadata()

    elements = apply_lang_metadata(
        [Table(text=text, metadata=metadata)],
        languages=languages,
    )
    return list(elements)
