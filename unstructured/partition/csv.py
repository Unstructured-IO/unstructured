from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

import pandas as pd
from lxml.html.soupparser import fromstring as soupparser_fromstring

from unstructured.chunking.title import add_chunking_strategy
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

DETECTION_ORIGIN: str = "csv"


@process_metadata()
@add_metadata_with_filetype(FileType.CSV)
@add_chunking_strategy()
def partition_csv(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    include_metadata: bool = True,
    languages: Optional[List[str]] = ["auto"],
    # NOTE (jennings) partition_csv generates a single TableElement
    # so detect_language_per_element is not included as a param
    **kwargs,
) -> List[Element]:
    """Partitions Microsoft Excel Documents in .csv format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_filename
        The filename to use for the metadata.
    metadata_last_modified
        The last modified date for the document.
    include_metadata
        Determines whether or not metadata is included in the output.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
    """
    exactly_one(filename=filename, file=file)

    if filename:
        table = pd.read_csv(filename, header=None)
        last_modification_date = get_last_modified_date(filename)

    elif file:
        last_modification_date = get_last_modified_date_from_file(file)
        f = spooled_to_bytes_io_if_needed(
            cast(Union[BinaryIO, SpooledTemporaryFile], file),
        )
        table = pd.read_csv(f, header=None)

    html_text = table.to_html(index=False, header=False, na_rep="")
    text = soupparser_fromstring(html_text).text_content()

    if include_metadata:
        metadata = ElementMetadata(
            text_as_html=html_text,
            filename=metadata_filename or filename,
            last_modified=metadata_last_modified or last_modification_date,
            languages=languages,
        )
    else:
        metadata = ElementMetadata()

    elements = apply_lang_metadata(
        [Table(text=text, metadata=metadata, detection_origin=DETECTION_ORIGIN)],
        languages=languages,
    )

    return list(elements)
