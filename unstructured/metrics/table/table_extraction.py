from typing import Any, Dict, List

from bs4 import BeautifulSoup

EMPTY_CELL = {
    "row_index": "",
    "col_index": "",
    "content": "",
}


def convert_table_from_markdown(markdown_str: str) -> List[Dict[str, Any]]:
    lines = markdown_str.split("\n")
    tables = []
    table = []
    in_table = False

    for i, line in enumerate(lines):
        if "|" in line:
            if not in_table:
                # Assuming first row is headers
                in_table = True

                # strip leading and trailing whitespaces and '|'
                line = line.strip().strip("|")

                # Split each table cell content by '|'
                cells = line.split("|")

                # For each cell construct the dictionary {row_index, col_index, content}
                for j, cell in enumerate(cells):
                    table.append({"row_index": 0, "col_index": j, "content": cell.strip()})

            else:
                # we are in the middle of a table
                # strip leading and trailing whitespaces and '|'
                line = line.strip().strip("|")

                cells = line.split("|")
                for j, cell in enumerate(cells):
                    table.append(
                        {
                            "row_index": len(table) // len(cells),
                            "col_index": j,
                            "content": cell.strip(),
                        }
                    )
        else:
            if in_table:
                # end of a table
                in_table = False
                tables.append(table)
                table = []

    if in_table:
        # the last table didn't end with a blank line
        tables.append(table)

    return tables


def _convert_table_from_html(content: str) -> List[Dict[str, Any]]:
    """Convert html format to table structure.

    Args:
        content: The html content with a table to extract.

    Returns:
        A list of dictionaries where each dictionary represents a cell in the table.
    """
    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table")
    rows = table.findAll(["tr", "thead"])
    table_data = []

    for i, row in enumerate(rows):
        headers = row.findAll("th")
        data_row = row.findAll("td")

        if headers:
            for j, header in enumerate(headers):
                cell = {
                    "row_index": i,
                    "col_index": j,
                    "content": header.text,
                }
                table_data.append(cell)

        if data_row:
            for k, data in enumerate(data_row):
                cell = {
                    "row_index": i,
                    "col_index": k,
                    "content": data.text,
                }
                table_data.append(cell)
    return table_data


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
    file_elements: List[Dict[str, Any]], prediction_table_format: str = "html"
) -> List[List[Dict[str, Any]]]:
    """Extracts and converts table data to a structured format based on the specified table type.

    Args:
      file_elements: List of elements from the file.
      table_type: The type of table format.

    Returns:
      A list of tables with each table represented as a list of cell data dictionaries.

    """
    if prediction_table_format == "html":
        return extract_and_convert_tables_from_html_prediction(file_elements)
    # a hack for now
    return file_elements


def extract_and_convert_tables_from_html_prediction(
    file_elements: List[Dict[str, Any]]
) -> List[List[Dict[str, Any]]]:
    """Extracts and converts table data to a structured format based on the specified table type.

    Args:
      file_elements: List of elements from the file.
      table_type: The type of table format.

    Returns:
      A list of tables with each table represented as a list of cell data dictionaries.

    """

    predicted_table_data = []
    for element in file_elements:
        if element.get("type") == "Table":
            val = element["metadata"].get("text_as_html")
            if not val or "<table>" not in val:
                continue
            try:
                converted_data = _convert_table_from_html(val)
                predicted_table_data.append(_sort_table_cells(converted_data))
            except Exception as e:
                print(f"Error converting Unstructured table data: {e}")
                predicted_table_data.append({})

    return predicted_table_data
