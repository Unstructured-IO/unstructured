from __future__ import annotations

from typing import Any, Dict, List

from bs4 import BeautifulSoup
from unstructured_inference.models.tables import cells_to_html

EMPTY_CELL = {
    "row_index": "",
    "col_index": "",
    "content": "",
}


def _move_cells_for_spanned_cells(cells: List[Dict[str, Any]]):
    """Move cells to the right if spanned cells have an influence on the rendering.

    Args:
        cells: List of cells in the table in Deckerd format.

    Returns:
        List of cells in the table in Deckerd format with cells moved to the right if spanned.
    """
    sorted_cells = sorted(cells, key=lambda x: (x["y"], x["x"]))
    cells_occupied_by_spanned = set()
    for cell in sorted_cells:
        if cell["w"] > 1 or cell["h"] > 1:
            for i in range(cell["y"], cell["y"] + cell["h"]):
                for j in range(cell["x"], cell["x"] + cell["w"]):
                    if (i, j) != (cell["y"], cell["x"]):
                        cells_occupied_by_spanned.add((i, j))
        while (cell["y"], cell["x"]) in cells_occupied_by_spanned:
            cell_y, cell_x = cell["y"], cell["x"]
            cells_to_the_right = [c for c in sorted_cells if c["y"] == cell_y and c["x"] >= cell_x]
            for cell_to_move in cells_to_the_right:
                cell_to_move["x"] += 1
            cells_occupied_by_spanned.remove((cell_y, cell_x))
    return sorted_cells


def html_table_to_deckerd(content: str) -> List[Dict[str, Any]]:
    """Convert html format to Deckerd table structure.

    Args:
        content: The html content with a table to extract.

    Returns:
        A list of dictionaries where each dictionary represents a cell in the table.
    """

    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table")
    rows = table.findAll(["tr"])
    table_data = []

    for i, row in enumerate(rows):
        cells = row.findAll(["th", "td"])
        for j, cell_data in enumerate(cells):
            cell = {
                "y": i,
                "x": j,
                "w": int(cell_data.attrs.get("colspan", 1)),
                "h": int(cell_data.attrs.get("rowspan", 1)),
                "content": cell_data.text,
            }
            table_data.append(cell)
    return _move_cells_for_spanned_cells(table_data)


def deckerd_table_to_html(cells: List[Dict[str, Any]]) -> str:
    """Convert Deckerd table structure to html format.

    Args:
        cells: List of dictionaries where each dictionary represents a cell in the table.

    Returns:
        A string with the html content of the table.
    """
    transformer_cells = []
    # determine which cells are in header. Consider row 0 as header
    # but spans may make it larger
    first_row_cells = [cell for cell in cells if cell["y"] == 0]
    header_length = max(cell["w"] for cell in first_row_cells)
    header_rows = set(range(header_length))
    for cell in cells:
        cell_data = {
            "row_nums": list(range(cell["y"], cell["y"] + cell["h"])),
            "column_nums": list(range(cell["x"], cell["x"] + cell["w"])),
            "w": cell["w"],
            "h": cell["h"],
            "cell text": cell["content"],
            "column header": cell["y"] in header_rows,
        }
        transformer_cells.append(cell_data)
    # reuse the existing function to convert to HTML
    table = cells_to_html(transformer_cells)
    return table


def _convert_table_from_html(content: str) -> List[Dict[str, Any]]:
    """Convert html format to table structure. As a middle step it converts
    html to the Deckerd format as it's more convenient to work with.

    Args:
        content: The html content with a table to extract.

    Returns:
        A list of dictionaries where each dictionary represents a cell in the table.
    """
    deckerd_cells = html_table_to_deckerd(content)
    return _convert_table_from_deckerd(deckerd_cells)


def _convert_table_from_deckerd(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert deckerd format to table structure.

    Args:
      content: The deckerd formatted content with a table to extract.

    Returns:
      A list of dictionaries where each dictionary represents a cell in the table.
    """
    table_data = []
    for table in content:
        try:
            cell_data = {
                "row_index": table["y"],
                "col_index": table["x"],
                "content": table["content"],
            }
        except KeyError:
            cell_data = EMPTY_CELL
        except TypeError:
            cell_data = EMPTY_CELL
        table_data.append(cell_data)
    return table_data


def _sort_table_cells(table_data: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
    return sorted(table_data, key=lambda cell: (cell["row_index"], cell["col_index"]))


def extract_and_convert_tables_from_ground_truth(
    file_elements: List[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """Extracts and converts tables data to a structured format based on the specified table type.

    Args:
        file_elements: List of elements from the ground truth file.

    Returns:
        A list of tables with each table represented as a list of cell data dictionaries.

    """
    ground_truth_table_data = []
    for element in file_elements:
        if "type" in element and element["type"] == "Table" and "text" in element:
            try:
                converted_data = _convert_table_from_deckerd(
                    element["text"],
                )
                ground_truth_table_data.append(_sort_table_cells(converted_data))
            except Exception as e:
                print(f"Error converting ground truth data: {e}")
                ground_truth_table_data.append({})

    return ground_truth_table_data


def extract_and_convert_tables_from_prediction(
    file_elements: List[Dict[str, Any]], source_type: str = "html"
) -> List[List[Dict[str, Any]]]:
    """Extracts and converts table data to a structured format

    Args:
      file_elements: List of elements from the file.
      source_type: 'cells' or 'html'. 'cells' refers to reading 'table_as_cells' field while
        'html' is extracted from 'text_as_html'

    Returns:
      A list of tables with each table represented as a list of cell data dictionaries.

    """
    source_type_to_extraction_strategies = {
        "html": extract_cells_from_text_as_html,
        "cells": extract_cells_from_table_as_cells,
    }
    if source_type not in source_type_to_extraction_strategies:
        raise ValueError(
            f'source_type {source_type} is not valid. Allowed source_types are "html" and "cells"'
        )

    extract_cells_fn = source_type_to_extraction_strategies[source_type]
    fallback_extract_cells_fn = (
        extract_cells_from_table_as_cells
        if source_type == "cells"
        else extract_cells_from_text_as_html
    )

    predicted_table_data = []
    for element in file_elements:
        if element.get("type") == "Table":
            extracted_cells = extract_cells_fn(element)
            if not extracted_cells:
                extracted_cells = fallback_extract_cells_fn(element)
            if extracted_cells:
                sorted_cells = _sort_table_cells(extracted_cells)
                predicted_table_data.append(sorted_cells)

    return predicted_table_data


def extract_cells_from_text_as_html(element: Dict[str, Any]) -> List[Dict[str, Any]] | None:
    """Extracts and parse cells from "text_as_html" field in Element structure

    Args:
        element: Example element:
        {
            "type": "Table",
            "metadata": {
                "text_as_html": "<table>
                                    <thead>
                                        <tr>
                                            <th>Month A.</th>
                                        </tr>
                                    </thead>
                                    </tbody>
                                        <tr>
                                            <td>22</td><
                                        </tr>
                                    </tbody>
                                </table>"
            }
        }

    Returns:
        List of extracted cells in a format:
        [
            {
                "row_index": 0,
                "col_index": 0,
                "content": "Month A.",
            },
            ...,
        ]
    """
    val = element["metadata"].get("text_as_html")
    if not val or "<table>" not in val:
        return None

    predicted_cells = None
    try:
        predicted_cells = _convert_table_from_html(val)
    except Exception as e:
        print(f"Error converting Unstructured table data: {e}")

    return predicted_cells


def extract_cells_from_table_as_cells(element: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts and parse cells from "table_as_cells" field in Element structure

    Args:
        element: Example element:
        {
            "type": "Table",
            "metadata": {
                "table_as_cells": [{"x": 0, "y": 0, "w": 1, "h": 1, "content": "Month A."},
                                   {"x": 0, "y": 1, "w": 1, "h": 1, "content": "22"}]
            }
        }

    Returns:
        List of extracted cells in a format:
        [
            {
                "row_index": 0,
                "col_index": 0,
                "content": "Month A.",
            },
            ...,
        ]
    """
    predicted_cells = element["metadata"].get("table_as_cells")
    converted_cells = None
    if predicted_cells:
        converted_cells = _convert_table_from_deckerd(predicted_cells)
    return converted_cells
