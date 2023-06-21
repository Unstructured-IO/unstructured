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
from unstructured.partition.common import exactly_one, spooled_to_bytes_io_if_needed


@process_metadata()
@add_metadata_with_filetype(FileType.CSV)
def partition_csv(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
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
    include_metadata
        Determines whether or not metadata is included in the output.
    """
    exactly_one(filename=filename, file=file)

    if filename:
        table = pd.read_csv(filename)
    else:
        f = spooled_to_bytes_io_if_needed(cast(Union[BinaryIO, SpooledTemporaryFile], file))
        table = pd.read_csv(f)

    metadata_filename = filename or metadata_filename

    html_text = table.to_html(index=False, header=False, na_rep="")
    text = lxml.html.document_fromstring(html_text).text_content()

    if include_metadata:
        metadata = ElementMetadata(
            text_as_html=html_text,
            filename=metadata_filename,
        )
    else:
        metadata = ElementMetadata()

    return [Table(text=text, metadata=metadata)]
