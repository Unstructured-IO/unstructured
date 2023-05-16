from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

import lxml.html
import pandas as pd

from unstructured.documents.elements import Element, ElementMetadata, Table
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import exactly_one, spooled_to_bytes_io_if_needed


@add_metadata_with_filetype(FileType.XLSX)
def partition_xlsx(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
) -> List[Element]:
    """Partitions Microsoft Excel Documents in .xlsx format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_filename
        The filename to use for the metadata. Relevant because partition_doc converts the
        document to .xlsx before partition. We want the original source filename in the
        metadata.
    """
    exactly_one(filename=filename, file=file)

    if filename:
        sheets = pd.read_excel(filename, sheet_name=None)
    else:
        f = spooled_to_bytes_io_if_needed(cast(Union[BinaryIO, SpooledTemporaryFile], file))
        sheets = pd.read_excel(f, sheet_name=None)

    elements: List[Element] = []
    page_number = 0
    for sheet_name, table in sheets.items():
        page_number += 1
        html_text = table.to_html(index=False, header=False, na_rep="")
        text = lxml.html.document_fromstring(html_text).text_content()

        metadata = ElementMetadata(
            text_as_html=html_text,
            page_number=page_number,
            filename=filename,
        )
        table = Table(text=text, metadata=metadata)
        elements.append(table)

    return elements
