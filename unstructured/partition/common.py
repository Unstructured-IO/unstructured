from __future__ import annotations

import subprocess
from io import BufferedReader, BytesIO, TextIOWrapper
from tempfile import SpooledTemporaryFile
from typing import IO, TYPE_CHECKING, Any, BinaryIO, Dict, List, Optional, Tuple, Union

from docx import table as docxtable
from tabulate import tabulate

from unstructured.documents.elements import (
    TYPE_TO_TEXT_ELEMENT_MAP,
    CheckBox,
    Element,
    ElementMetadata,
    ListItem,
    PageBreak,
    Text,
)
from unstructured.logger import logger
from unstructured.nlp.patterns import ENUMERATED_BULLETS_RE, UNICODE_BULLETS_RE

if TYPE_CHECKING:
    from unstructured_inference.inference.layoutelement import LayoutElement


def normalize_layout_element(
    layout_element: Union["LayoutElement", Element, Dict[str, Any]],
) -> Union[Element, List[Element]]:
    """Converts an unstructured_inference LayoutElement object to an unstructured Element."""

    if isinstance(layout_element, Element):
        return layout_element

    # NOTE(alan): Won't the lines above ensure this never runs (PageBreak is a subclass of Element)?
    if isinstance(layout_element, PageBreak):
        return PageBreak()

    if not isinstance(layout_element, dict):
        layout_dict = layout_element.to_dict()
    else:
        layout_dict = layout_element

    text = layout_dict.get("text")
    coordinates = layout_dict.get("coordinates")
    element_type = layout_dict.get("type")

    if element_type == "List":
        return layout_list_to_list_items(text, coordinates)
    elif element_type in TYPE_TO_TEXT_ELEMENT_MAP:
        _element_class = TYPE_TO_TEXT_ELEMENT_MAP[element_type]
        return _element_class(text=text, coordinates=coordinates)
    elif element_type == "Checked":
        return CheckBox(checked=True, coordinates=coordinates)
    elif element_type == "Unchecked":
        return CheckBox(checked=False, coordinates=coordinates)
    else:
        return Text(text=text, coordinates=coordinates)


def layout_list_to_list_items(
    text: str,
    coordinates: Tuple[Tuple[float, float], ...],
) -> List[Element]:
    """Converts a list LayoutElement to a list of ListItem elements."""
    split_items = ENUMERATED_BULLETS_RE.split(text)
    # NOTE(robinson) - this means there wasn't a match for the enumerated bullets
    if len(split_items) == 1:
        split_items = UNICODE_BULLETS_RE.split(text)

    list_items: List[Element] = []
    for text_segment in split_items:
        if len(text_segment.strip()) > 0:
            list_items.append(
                ListItem(text=text_segment.strip(), coordinates=coordinates),
            )

    return list_items


def _add_element_metadata(
    element: Element,
    filename: Optional[str] = None,
    filetype: Optional[str] = None,
    page_number: Optional[int] = None,
    url: Optional[str] = None,
    text_as_html: Optional[str] = None,
) -> Element:
    """Adds document metadata to the document element. Document metadata includes information
    like the filename, source url, and page number."""
    metadata = ElementMetadata(
        filename=filename,
        filetype=filetype,
        page_number=page_number,
        url=url,
        text_as_html=text_as_html,
    )
    element.metadata = metadata.merge(element.metadata)
    return element


def _remove_element_metadata(
    layout_elements,
) -> List[Element]:
    """Removes document metadata from the document element. Document metadata includes information
    like the filename, source url, and page number."""
    # Init an empty list of elements to write to
    elements: List[Element] = []
    metadata = ElementMetadata()
    for layout_element in layout_elements:
        element = normalize_layout_element(layout_element)
        if isinstance(element, list):
            for _element in element:
                _element.metadata = metadata
            elements.extend(element)
        else:
            element.metadata = metadata
            elements.append(element)
    return elements


def convert_office_doc(input_filename: str, output_directory: str, target_format: str):
    """Converts a .doc file to a .docx file using the libreoffice CLI."""
    # NOTE(robinson) - In the future can also include win32com client as a fallback for windows
    # users who do not have LibreOffice installed
    # ref: https://stackoverflow.com/questions/38468442/
    #       multiple-doc-to-docx-file-conversion-using-python
    command = [
        "soffice",
        "--headless",
        "--convert-to",
        target_format,
        "--outdir",
        output_directory,
        input_filename,
    ]
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        output, error = process.communicate()
    except FileNotFoundError:
        raise FileNotFoundError(
            """soffice command was not found. Please install libreoffice
on your system and try again.

- Install instructions: https://www.libreoffice.org/get-help/install-howto/
- Mac: https://formulae.brew.sh/cask/libreoffice
- Debian: https://wiki.debian.org/LibreOffice""",
        )

    logger.info(output.decode().strip())
    if error:
        logger.error(error.decode().strip())


def exactly_one(**kwargs) -> None:
    """
    Verify arguments; exactly one of all keyword arguments must not be None.

    Example:
        >>> exactly_one(filename=filename, file=file, text=text, url=url)
    """
    if sum([(arg is not None and arg != "") for arg in kwargs.values()]) != 1:
        names = list(kwargs.keys())
        if len(names) > 1:
            message = f"Exactly one of {', '.join(names[:-1])} and {names[-1]} must be specified."
        else:
            message = f"{names[0]} must be specified."
        raise ValueError(message)


def spooled_to_bytes_io_if_needed(
    file_obj: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]],
) -> Optional[Union[bytes, BinaryIO]]:
    if isinstance(file_obj, SpooledTemporaryFile):
        file_obj.seek(0)
        contents = file_obj.read()
        return BytesIO(contents)
    else:
        # Return the original file object if it's not a SpooledTemporaryFile
        return file_obj


def convert_to_bytes(
    file: Optional[Union[bytes, SpooledTemporaryFile, IO]] = None,
) -> bytes:
    if isinstance(file, bytes):
        f_bytes = file
    elif isinstance(file, SpooledTemporaryFile):
        file.seek(0)
        f_bytes = file.read()
    elif isinstance(file, BytesIO):
        f_bytes = file.getvalue()
    elif isinstance(file, (TextIOWrapper, BufferedReader)):
        with open(file.name, "rb") as f:
            f_bytes = f.read()
    else:
        raise ValueError("Invalid file-like object type")

    return f_bytes


def convert_ms_office_table_to_text(table: docxtable.Table, as_html: bool = True):
    """
    Convert a table object from a Word document to an HTML table string using the tabulate library.

    Args:
        table (Table): A Table object.
        as_html (bool): Whether to return the table as an HTML string (True) or a
            plain text string (False)

    Returns:
        str: An table string representation of the input table.
    """
    fmt = "html" if as_html else "plain"
    rows = list(table.rows)
    headers = [cell.text for cell in rows[0].cells]
    data = [[cell.text for cell in row.cells] for row in rows[1:]]
    return tabulate(data, headers=headers, tablefmt=fmt)
