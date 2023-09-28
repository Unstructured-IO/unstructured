from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

import pandas as pd
from lxml.html.soupparser import fromstring as soupparser_fromstring

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
@add_metadata_with_filetype(FileType.XLSX)
def partition_xlsx(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    metadata_last_modified: Optional[str] = None,
    include_header: bool = True,
    **kwargs,
) -> List[Element]:
    """Partitions Microsoft Excel Documents in .xlsx format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_metadata
        Determines whether or not metadata is included in the output.
    metadata_last_modified
        The day of the last modification
    include_header
        Determines whether or not header info info is included in text and medatada.text_as_html
    """
    exactly_one(filename=filename, file=file)
    last_modification_date = None
    if filename:
        sheets = pd.read_excel(filename, sheet_name=None, header=None)
        last_modification_date = get_last_modified_date(filename)

    elif file:
        f = spooled_to_bytes_io_if_needed(
            cast(Union[BinaryIO, SpooledTemporaryFile], file),
        )
        sheets = pd.read_excel(f, sheet_name=None, header=None)
        last_modification_date = get_last_modified_date_from_file(file)

    # connected_components: List[dict] = []
    # for sheet in sheets:
    #     connected_components.append(_find_connected_components(sheet))

    elements: List[Element] = []
    page_number = 0
    for sheet_name, table in sheets.items():
        breakpoint()
        page_number += 1
        html_text = table.to_html(index=False, header=include_header, na_rep="")
        text = soupparser_fromstring(html_text).text_content()

        if include_metadata:
            metadata = ElementMetadata(
                text_as_html=html_text,
                page_name=sheet_name,
                page_number=page_number,
                filename=metadata_filename or filename,
                last_modified=metadata_last_modified or last_modification_date,
            )
        else:
            metadata = ElementMetadata()

        table = Table(text=text, metadata=metadata)
        elements.append(table)

    return elements


def _find_connected_components(sheet_name, sheet):
    max_row, max_col = sheet.shape
    visited = set()
    connected_components = []

    def dfs(row, col, component):
        if (
            row < 0
            or row >= sheet.shape[0]
            or col < 0
            or col >= sheet.shape[1]
            or (row, col) in visited
        ):
            return
        visited.add((row, col))

        if not pd.isna(sheet.iat[row, col]):
            component.append((row, col))

            # Explore neighboring cells
            dfs(row - 1, col, component)  # Above
            dfs(row + 1, col, component)  # Below
            dfs(row, col - 1, component)  # Left
            dfs(row, col + 1, component)  # Right

    for row in range(max_row):
        for col in range(max_col):
            if (row, col) not in visited:
                if not pd.isna(sheet.iat[row, col]):
                    component = []
                    dfs(row, col, component)
                    connected_components.append(component)
                    
    min_x, min_y, max_x, max_y = _find_min_max_coords(connected_components)
    return connected_components, (min_x, min_y, max_x, max_y)

def _find_min_max_coords(connected_components):
    pass

def _make_rectangular():
    pass