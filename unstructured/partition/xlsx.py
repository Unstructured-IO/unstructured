from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Tuple, Union, cast

import numpy as np
import pandas as pd
from lxml.html.soupparser import fromstring as soupparser_fromstring

from unstructured.cleaners.core import clean_bullets
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
    process_metadata,
)
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
    spooled_to_bytes_io_if_needed,
)

# from unstructured.partition.lang import detect_languages
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_possible_narrative_text,
    is_possible_numbered_list,
    is_possible_title,
)


@process_metadata()
@add_metadata_with_filetype(FileType.XLSX)
def partition_xlsx(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    metadata_last_modified: Optional[str] = None,
    include_header: bool = False,
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
    header = 0 if include_header else None

    if filename:
        sheets = pd.read_excel(filename, sheet_name=None, header=header)
        last_modification_date = get_last_modified_date(filename)

    elif file:
        f = spooled_to_bytes_io_if_needed(
            cast(Union[BinaryIO, SpooledTemporaryFile], file),
        )
        sheets = pd.read_excel(f, sheet_name=None, header=header)
        last_modification_date = get_last_modified_date_from_file(file)

    elements: List[Element] = []
    page_number = 0
    for sheet_name, sheet in sheets.items():
        page_number += 1
        _connected_components = _get_connected_components(sheet)
        for _connected_component, _min_max_coords in _connected_components:
            min_x, min_y, max_x, max_y = _min_max_coords

            subtable = sheet.iloc[min_x : max_x + 1, min_y : max_y + 1]  # noqa: E203
            single_non_empty_rows, single_non_empty_row_contents = _single_non_empty_rows(
                subtable,
            )
            front_non_consecutive, last_non_consecutive = _find_first_and_last_non_consecutive_row(
                single_non_empty_rows,
            )

            # NOTE(klaijan) - need to explicitly define the condition to avoid the case of 0
            if front_non_consecutive is not None and last_non_consecutive is not None:
                first_row = front_non_consecutive - max_x
                last_row = max_x - last_non_consecutive
                subtable = _get_sub_subtable(subtable, (first_row, last_row))

            # detect_languages

            if include_metadata:
                metadata = ElementMetadata(
                    page_name=sheet_name,
                    page_number=page_number,
                    filename=metadata_filename or filename,
                    last_modified=metadata_last_modified or last_modification_date,
                )
            else:
                metadata = ElementMetadata()

            if front_non_consecutive is not None:
                for content in single_non_empty_row_contents[: front_non_consecutive + 1]:
                    element = _check_content_element_type(str(content))
                    element.metadata = metadata
                    elements.append(element)

            if subtable is not None and len(subtable) == 1:
                element = _check_content_element_type(str(subtable.iloc[0].values[0]))
                element.metadata = metadata
                elements.append(element)

            elif subtable is not None:
                # parse subtables as html
                html_text = subtable.to_html(index=False, header=include_header, na_rep="")
                text = soupparser_fromstring(html_text).text_content()

                table_metadata = metadata
                table_metadata.text_as_html = html_text

                subtable = Table(text=text, metadata=table_metadata)
                elements.append(subtable)

            if front_non_consecutive is not None and last_non_consecutive is not None:
                for content in single_non_empty_row_contents[
                    front_non_consecutive + 1 :  # noqa: E203
                ]:
                    element = _check_content_element_type(str(content))
                    element.metadata = metadata
                    elements.append(element)

    return elements


def _get_connected_components(sheet, filter=True):
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
            if (row, col) not in visited and not pd.isna(sheet.iat[row, col]):
                component: List[dict] = []
                dfs(row, col, component)
                min_x, min_y, max_x, max_y = _find_min_max_coord(component)
                connected_components.append(
                    {
                        "component": component,
                        "min_x": min_x,
                        "min_y": min_y,
                        "max_x": max_x,
                        "max_y": max_y,
                    }
                )
    if filter:
        connected_components = _filter_overlapping_tables(connected_components)
    return [
        (
            connected_component["component"],
            (
                connected_component["min_x"],
                connected_component["min_y"],
                connected_component["max_x"],
                connected_component["max_y"],
            ),
        )
        for connected_component in connected_components
    ]


def _filter_overlapping_tables(connected_components):
    sorted_components = sorted(connected_components, key=lambda x: x["min_x"])
    merged_components: List[dict] = []
    current_component = None
    for component in sorted_components:
        if current_component is None:
            current_component = component
        else:
            # Check if component overlaps with the current_component
            if component["min_x"] <= current_component["max_x"]:
                # Merge the components and update min_x, max_x
                current_component["component"].extend(component["component"])
                current_component["min_x"] = min(current_component["min_x"], component["min_x"])
                current_component["max_x"] = max(current_component["max_x"], component["max_x"])
                current_component["min_y"] = min(current_component["min_y"], component["min_y"])
                current_component["max_y"] = max(current_component["max_y"], component["max_y"])
            if component["min_y"] <= current_component["max_y"]:
                # Merge the components and update min_y, max_y
                current_component["component"].extend(component["component"])
                current_component["min_x"] = min(current_component["min_x"], component["min_x"])
                current_component["max_x"] = max(current_component["max_x"], component["max_x"])
                current_component["min_y"] = min(current_component["min_y"], component["min_y"])
                current_component["max_y"] = max(current_component["max_y"], component["max_y"])
            else:
                # No overlap, add the current_component to the merged list
                merged_components.append(current_component)
                # Update the current_component
                current_component = component
    # Append the last current_component to the merged list
    if current_component is not None:
        merged_components.append(current_component)
    return merged_components


def _check_overlaps_components(min_max_coord1, min_max_coord2):
    return


def _find_min_max_coord(connected_component):
    min_x, min_y, max_x, max_y = float("inf"), float("inf"), float("-inf"), float("-inf")
    for _x, _y in connected_component:
        if _x < min_x:
            min_x = _x
        if _y < min_y:
            min_y = _y
        if _x > max_x:
            max_x = _x
        if _y > max_y:
            max_y = _y
    return min_x, min_y, max_x, max_y


def _get_sub_subtable(subtable: pd.DataFrame, first_and_last_row: Tuple[int, int]) -> pd.DataFrame:
    # TODO(klaijan) - to further check for sub subtable, we could check whether
    # two consecutive rows contains full row of cells.
    # if yes, it might not be a header. We should check the length.
    first_row, last_row = first_and_last_row
    if last_row == first_row:
        return None
    return subtable.iloc[first_row : last_row + 1]  # noqa: E203


def _find_first_and_last_non_consecutive_row(
    row_indices: List[int],
) -> Tuple[Optional[int], Optional[int]]:
    # NOTE(klaijan) - only consider non-table rows for consecutive top or bottom rows
    if len(row_indices) == 1:
        return row_indices[0], row_indices[0]

    arr = np.array(row_indices)
    front_non_consecutive = next(
        (i for i, (x, y) in enumerate(zip(arr, arr[1:])) if x + 1 != y),
        None,
    )
    reversed_arr = arr[::-1]  # Reverse the array
    last_non_consecutive = next(
        (i for i, (x, y) in enumerate(zip(reversed_arr, reversed_arr[1:])) if x - 1 != y),
        None,
    )
    return front_non_consecutive, last_non_consecutive


def _single_non_empty_rows(subtable) -> Tuple[List[int], List[str]]:
    single_non_empty_rows = []
    single_non_empty_row_contents = []
    for index, row in subtable.iterrows():
        if row.count() == 1:
            single_non_empty_rows.append(index)
            single_non_empty_row_contents.append(row.dropna().iloc[0])
    return single_non_empty_rows, single_non_empty_row_contents


def _check_content_element_type(text: str) -> Element:
    if is_bulleted_text(text):
        return ListItem(
            text=clean_bullets(text),
        )
    elif is_possible_numbered_list(text):
        return ListItem(
            text=text,
        )
    elif is_possible_narrative_text(text):
        return NarrativeText(
            text=text,
        )
    elif is_possible_title(text):
        return Title(
            text=text,
        )
    else:
        return Text(
            text=text,
        )


# add language
