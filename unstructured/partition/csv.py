import csv
from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

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

DETECTION_ORIGIN: str = "csv"


@process_metadata()
@add_metadata_with_filetype(FileType.CSV)
@add_chunking_strategy
def partition_csv(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    include_header: bool = False,
    include_metadata: bool = True,
    infer_table_structure: bool = True,
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
    include_header
        Determines whether or not header info info is included in text and medatada.text_as_html.
    include_metadata
        Determines whether or not metadata is included in the output.
    infer_table_structure
        If True, any Table elements that are extracted will also have a metadata field
        named "text_as_html" where the table's text content is rendered into an html string.
        I.e., rows and cells are preserved.
        Whether True or False, the "text" field is always present in any Table element
        and is the text content of the table (no structure).
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
    """
    exactly_one(filename=filename, file=file)

    header = 0 if include_header else None

    if filename:
        delimiter = get_delimiter(file_path=filename)
        table = pd.read_csv(filename, header=header, sep=delimiter)
        last_modification_date = get_last_modified_date(filename)

    elif file:
        last_modification_date = get_last_modified_date_from_file(file)
        f = spooled_to_bytes_io_if_needed(
            cast(Union[BinaryIO, SpooledTemporaryFile], file),
        )
        delimiter = get_delimiter(file=f)
        table = pd.read_csv(f, header=header, sep=delimiter)

    html_text = table.to_html(index=False, header=include_header, na_rep="")
    text = soupparser_fromstring(html_text).text_content()

    if include_metadata:
        metadata = ElementMetadata(
            filename=metadata_filename or filename,
            last_modified=metadata_last_modified or last_modification_date,
            languages=languages,
        )
        if infer_table_structure:
            metadata.text_as_html = html_text
    else:
        metadata = ElementMetadata()

    elements = apply_lang_metadata(
        [Table(text=text, metadata=metadata, detection_origin=DETECTION_ORIGIN)],
        languages=languages,
    )

    return list(elements)


def get_delimiter(file_path=None, file=None):
    """
    Use the standard csv sniffer to determine the delimiter.
    Read just a small portion in case the file is large.
    """
    sniffer = csv.Sniffer()

    num_bytes = 8192
    if file:
        data = file.read(num_bytes).decode("utf-8")
        file.seek(0)
    else:
        with open(file_path) as f:
            data = f.read(num_bytes)

    return sniffer.sniff(data, delimiters=[",", ";"]).delimiter
