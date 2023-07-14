from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

import lxml.html
import pandas as pd

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


@process_metadata()
@add_metadata_with_filetype(FileType.TSV)
def partition_tsv(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
    metadata_date: Optional[str] = None,
    include_metadata: bool = True,
    **kwargs,
) -> List[Element]:
    """Partitions TSV files into document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_metadata
        Determines whether or not metadata is included in the output.
    metadata_date
        The day of the last modification
    """
    exactly_one(filename=filename, file=file)
    last_modification_date = None
    if filename:
        table = pd.read_csv(filename, sep="\t")
        last_modification_date = get_last_modified_date(filename)
    elif file:
        f = spooled_to_bytes_io_if_needed(
            cast(Union[BinaryIO, SpooledTemporaryFile], file),
        )
        table = pd.read_csv(f, sep="\t")
        last_modification_date = get_last_modified_date_from_file(file)

    html_text = table.to_html(index=False, header=False, na_rep="")
    text = lxml.html.document_fromstring(html_text).text_content()

    if include_metadata:
        metadata = ElementMetadata(
            text_as_html=html_text,
            filename=metadata_filename or filename,
            date=metadata_date or last_modification_date,
        )
    else:
        metadata = ElementMetadata()

    return [Table(text=text, metadata=metadata)]
