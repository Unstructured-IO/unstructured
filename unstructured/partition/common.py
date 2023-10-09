from __future__ import annotations

import numbers
import os
import subprocess
from datetime import datetime
from io import BufferedReader, BytesIO, TextIOWrapper
from tempfile import SpooledTemporaryFile
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import emoji
from tabulate import tabulate

from unstructured.documents.coordinates import CoordinateSystem, PixelSpace
from unstructured.documents.elements import (
    TYPE_TO_TEXT_ELEMENT_MAP,
    CheckBox,
    CoordinatesMetadata,
    Element,
    ElementMetadata,
    ListItem,
    PageBreak,
    Text,
    Title,
)
from unstructured.logger import logger
from unstructured.nlp.patterns import ENUMERATED_BULLETS_RE, UNICODE_BULLETS_RE
from unstructured.partition.utils.constants import (
    SORT_MODE_DONT,
    SORT_MODE_XY_CUT,
)
from unstructured.utils import dependency_exists, first

if dependency_exists("docx") and dependency_exists("docx.table"):
    from docx.table import Table as docxtable

if dependency_exists("pptx") and dependency_exists("pptx.table"):
    from pptx.table import Table as pptxtable

if dependency_exists("numpy") and dependency_exists("cv2"):
    from unstructured.partition.utils.sorting import sort_page_elements

if TYPE_CHECKING:
    from unstructured_inference.inference.layout import DocumentLayout, PageLayout
    from unstructured_inference.inference.layoutelement import LayoutElement


HIERARCHY_RULE_SET = {
    "Title": [
        "Text",
        "UncategorizedText",
        "NarrativeText",
        "ListItem",
        "BulletedText",
        "Table",
        "FigureCaption",
        "CheckBox",
        "Table",
    ],
    "Header": [
        "Title",
        "Text",
        "UncategorizedText",
        "NarrativeText",
        "ListItem",
        "BulletedText",
        "Table",
        "FigureCaption",
        "CheckBox",
        "Table",
    ],
}


def get_last_modified_date(filename: str) -> Union[str, None]:
    modify_date = datetime.fromtimestamp(os.path.getmtime(filename))
    return modify_date.strftime("%Y-%m-%dT%H:%M:%S%z")


def get_last_modified_date_from_file(
    file: Union[IO[bytes], SpooledTemporaryFile[bytes], BinaryIO, bytes],
) -> Union[str, None]:
    filename = None
    if hasattr(file, "name"):
        filename = file.name

    if not filename:
        return None

    modify_date = get_last_modified_date(filename)
    return modify_date


def normalize_layout_element(
    layout_element: Union[
        "LayoutElement",
        Element,
        Dict[str, Any],
    ],
    coordinate_system: Optional[CoordinateSystem] = None,
    infer_list_items: bool = True,
    source_format: Optional[str] = "html",
) -> Union[Element, List[Element]]:
    """Converts an unstructured_inference LayoutElement object to an unstructured Element."""

    if isinstance(layout_element, Element) and source_format == "html":
        return layout_element

    # NOTE(alan): Won't the lines above ensure this never runs (PageBreak is a subclass of Element)?
    if isinstance(layout_element, PageBreak):
        return PageBreak(text="")

    if not isinstance(layout_element, dict):
        layout_dict = layout_element.to_dict()
    else:
        layout_dict = layout_element

    text = layout_dict.get("text")
    # Both `coordinates` and `coordinate_system` must be present
    # in order to add coordinates metadata to the element.
    coordinates = layout_dict.get("coordinates")
    element_type = layout_dict.get("type")
    prob = layout_dict.get("prob")
    aux_origin = layout_dict["source"] if "source" in layout_dict else None
    origin = None
    if aux_origin:
        origin = aux_origin.value
    if prob and isinstance(prob, (int, str, float, numbers.Number)):
        class_prob_metadata = ElementMetadata(detection_class_prob=float(prob))  # type: ignore
    else:
        class_prob_metadata = ElementMetadata()
    if element_type == "List":
        if infer_list_items:
            return layout_list_to_list_items(
                text,
                coordinates=coordinates,
                coordinate_system=coordinate_system,
                metadata=class_prob_metadata,
                detection_origin=origin,
            )
        else:
            return ListItem(
                text=text if text else "",
                coordinates=coordinates,
                coordinate_system=coordinate_system,
                metadata=class_prob_metadata,
                detection_origin=origin,
            )

    elif element_type in TYPE_TO_TEXT_ELEMENT_MAP:
        _element_class = TYPE_TO_TEXT_ELEMENT_MAP[element_type]
        _element_class = _element_class(
            text=text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
            metadata=class_prob_metadata,
            detection_origin=origin,
        )
        if element_type == "Headline":
            _element_class.metadata.category_depth = 1
        elif element_type == "Subheadline":
            _element_class.metadata.category_depth = 2
        return _element_class
    elif element_type == "Checked":
        return CheckBox(
            checked=True,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
            metadata=class_prob_metadata,
            detection_origin=origin,
        )
    elif element_type == "Unchecked":
        return CheckBox(
            checked=False,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
            metadata=class_prob_metadata,
            detection_origin=origin,
        )
    else:
        return Text(
            text=text if text else "",
            coordinates=coordinates,
            coordinate_system=coordinate_system,
            metadata=class_prob_metadata,
            detection_origin=origin,
        )


def layout_list_to_list_items(
    text: Optional[str],
    coordinates: Optional[Tuple[Tuple[float, float], ...]],
    coordinate_system: Optional[CoordinateSystem],
    metadata=Optional[ElementMetadata],
    detection_origin=Optional[str],
) -> List[Element]:
    """Converts a list LayoutElement to a list of ListItem elements."""
    split_items = ENUMERATED_BULLETS_RE.split(text) if text else []
    # NOTE(robinson) - this means there wasn't a match for the enumerated bullets
    if len(split_items) == 1:
        split_items = UNICODE_BULLETS_RE.split(text) if text else []

    list_items: List[Element] = []
    for text_segment in split_items:
        if len(text_segment.strip()) > 0:
            # Both `coordinates` and `coordinate_system` must be present
            # in order to add coordinates metadata to the element.
            item = ListItem(
                text=text_segment.strip(),
                coordinates=coordinates,
                coordinate_system=coordinate_system,
                metadata=metadata,
                detection_origin=detection_origin,
            )
            list_items.append(item)

    return list_items


def set_element_hierarchy(
    elements: List[Element],
    ruleset: Dict[str, List[str]] = HIERARCHY_RULE_SET,
) -> List[Element]:
    """Sets the parent_id for each element in the list of elements
    based on the element's category, depth and a ruleset

    """
    stack: List[Element] = []
    for element in elements:
        if element.metadata.parent_id is not None:
            continue
        parent_id = None
        element_category = getattr(element, "category", None)
        element_category_depth = getattr(element.metadata, "category_depth", 0) or 0

        if not element_category:
            continue

        while stack:
            top_element: Element = stack[-1]
            top_element_category = getattr(top_element, "category")
            top_element_category_depth = (
                getattr(
                    top_element.metadata,
                    "category_depth",
                    0,
                )
                or 0
            )

            if (
                top_element_category == element_category
                and top_element_category_depth < element_category_depth
            ) or (
                top_element_category != element_category
                and element_category in ruleset.get(top_element_category, [])
            ):
                parent_id = top_element.id
                break

            stack.pop()

        element.metadata.parent_id = parent_id
        stack.append(element)

    return elements


def _add_element_metadata(
    element: Element,
    filename: Optional[str] = None,
    filetype: Optional[str] = None,
    page_number: Optional[int] = None,
    url: Optional[str] = None,
    text_as_html: Optional[str] = None,
    coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
    coordinate_system: Optional[CoordinateSystem] = None,
    section: Optional[str] = None,
    image_path: Optional[str] = None,
    detection_origin: Optional[str] = None,
    **kwargs,
) -> Element:
    """Adds document metadata to the document element. Document metadata includes information
    like the filename, source url, and page number."""

    coordinates_metadata = (
        CoordinatesMetadata(
            points=coordinates,
            system=coordinate_system,
        )
        if coordinates is not None and coordinate_system is not None
        else None
    )
    links = element.links if hasattr(element, "links") and len(element.links) > 0 else None
    link_urls = [link.get("url") for link in links] if links else None
    link_texts = [link.get("text") for link in links] if links else None
    emphasized_texts = (
        element.emphasized_texts
        if hasattr(element, "emphasized_texts") and len(element.emphasized_texts) > 0
        else None
    )
    emphasized_text_contents = (
        [emphasized_text.get("text") for emphasized_text in emphasized_texts]
        if emphasized_texts
        else None
    )
    emphasized_text_tags = (
        [emphasized_text.get("tag") for emphasized_text in emphasized_texts]
        if emphasized_texts
        else None
    )
    depth = element.metadata.category_depth if element.metadata.category_depth else None

    metadata = ElementMetadata(
        coordinates=coordinates_metadata,
        filename=filename,
        filetype=filetype,
        page_number=page_number,
        url=url,
        text_as_html=text_as_html,
        link_urls=link_urls,
        link_texts=link_texts,
        emphasized_text_contents=emphasized_text_contents,
        emphasized_text_tags=emphasized_text_tags,
        section=section,
        category_depth=depth,
        image_path=image_path,
    )
    metadata.detection_origin = detection_origin
    # NOTE(newel) - Element metadata is being merged into
    # newly constructed metadata, not the other way around
    # TODO? Make this more expected behavior?
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


def convert_office_doc(
    input_filename: str,
    output_directory: str,
    target_format: str = "docx",
    target_filter: Optional[str] = None,
):
    """Converts a .doc file to a .docx file using the libreoffice CLI.

    Parameters
    ----------
    input_filename: str
        The name of the .doc file to convert to .docx
    output_directory: str
        The output directory for the convert .docx file
    target_format: str
        The desired output format
    target_filter: str
        The output filter name to use when converting. See references below
        for details.

    References
    ----------
    https://stackoverflow.com/questions/52277264/convert-doc-to-docx-using-soffice-not-working
    https://git.libreoffice.org/core/+/refs/heads/master/filter/source/config/fragments/filters

    """
    if target_filter is not None:
        target_format = f"{target_format}:{target_filter}"
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


def exactly_one(**kwargs: Any) -> None:
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
    file_obj: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile[bytes]]],
) -> Optional[Union[bytes, BinaryIO]]:
    if isinstance(file_obj, SpooledTemporaryFile):
        file_obj.seek(0)
        contents = file_obj.read()
        return BytesIO(contents)
    else:
        # Return the original file object if it's not a SpooledTemporaryFile
        return file_obj


def convert_to_bytes(
    file: Optional[Union[bytes, SpooledTemporaryFile, IO[bytes]]] = None,
) -> bytes:
    if isinstance(file, bytes):
        f_bytes = file
    elif isinstance(file, SpooledTemporaryFile):
        file.seek(0)
        f_bytes = file.read()
        file.seek(0)
    elif isinstance(file, BytesIO):
        f_bytes = file.getvalue()
    elif isinstance(file, (TextIOWrapper, BufferedReader)):
        with open(file.name, "rb") as f:
            f_bytes = f.read()
    else:
        raise ValueError("Invalid file-like object type")

    return f_bytes


def convert_ms_office_table_to_text(
    table: Union["docxtable", "pptxtable"],
    as_html: bool = True,
) -> str:
    """
    Convert a table object from a Word document to an HTML table string using the tabulate library.

    Args:
        table (Table): A docx.table.Table object.
        as_html (bool): Whether to return the table as an HTML string (True) or a
            plain text string (False)

    Returns:
        str: An table string representation of the input table.
    """
    fmt = "html" if as_html else "plain"
    rows = list(table.rows)
    if len(rows) > 0:
        headers = [cell.text for cell in rows[0].cells]
        data = [[cell.text for cell in row.cells] for row in rows[1:]]
        table_text = tabulate(data, headers=headers, tablefmt=fmt)
    else:
        table_text = ""
    return table_text


def contains_emoji(s: str) -> bool:
    """
    Check if the input string contains any emoji characters.

    Parameters:
    - s (str): The input string to check.

    Returns:
    - bool: True if the string contains any emoji, False otherwise.
    """

    return bool(emoji.emoji_count(s))


def _get_page_image_metadata(
    page: PageLayout,
) -> dict:
    """Retrieve image metadata and coordinate system from a page."""

    image = getattr(page, "image", None)
    image_metadata = getattr(page, "image_metadata", None)

    if image:
        image_format = image.format
        image_width = image.width
        image_height = image.height
    elif image_metadata:
        image_format = image_metadata.get("format")
        image_width = image_metadata.get("width")
        image_height = image_metadata.get("height")
    else:
        image_format = None
        image_width = None
        image_height = None

    return {
        "format": image_format,
        "width": image_width,
        "height": image_height,
    }


def document_to_element_list(
    document: "DocumentLayout",
    sortable: bool = False,
    include_page_breaks: bool = False,
    last_modification_date: Optional[str] = None,
    infer_list_items: bool = True,
    source_format: Optional[str] = None,
    detection_origin: Optional[str] = None,
    **kwargs,
) -> List[Element]:
    """Converts a DocumentLayout object to a list of unstructured elements."""
    elements: List[Element] = []
    sort_mode = kwargs.get("sort_mode", SORT_MODE_XY_CUT)

    num_pages = len(document.pages)
    for i, page in enumerate(document.pages):
        page_elements: List[Element] = []

        page_image_metadata = _get_page_image_metadata(page)
        image_format = page_image_metadata.get("format")
        image_width = page_image_metadata.get("width")
        image_height = page_image_metadata.get("height")

        translation_mapping: List[Tuple["LayoutElement", Element]] = []
        for layout_element in page.elements:
            if image_width and image_height and hasattr(layout_element.bbox, "coordinates"):
                coordinate_system = PixelSpace(width=image_width, height=image_height)
            else:
                coordinate_system = None

            element = normalize_layout_element(
                layout_element,
                coordinate_system=coordinate_system,
                infer_list_items=infer_list_items,
                source_format=source_format if source_format else "html",
            )
            if isinstance(element, List):
                for el in element:
                    if last_modification_date:
                        el.metadata.last_modified = last_modification_date
                    el.metadata.page_number = i + 1
                page_elements.extend(element)
                translation_mapping.extend([(layout_element, el) for el in element])
                continue
            else:
                if last_modification_date:
                    element.metadata.last_modified = last_modification_date
                element.metadata.text_as_html = (
                    layout_element.text_as_html if hasattr(layout_element, "text_as_html") else None
                )
                try:
                    if (
                        isinstance(element, Title) and element.metadata.category_depth is None
                    ) and any(el.type in ["Headline", "Subheadline"] for el in page.elements):
                        element.metadata.category_depth = 0
                except AttributeError:
                    logger.info("HTML element instance has no attribute type")

                page_elements.append(element)
                translation_mapping.append((layout_element, element))
            coordinates = (
                element.metadata.coordinates.points if element.metadata.coordinates else None
            )

            el_image_path = (
                layout_element.image_path if hasattr(layout_element, "image_path") else None
            )

            _add_element_metadata(
                element,
                page_number=i + 1,
                filetype=image_format,
                coordinates=coordinates,
                coordinate_system=coordinate_system,
                category_depth=element.metadata.category_depth,
                image_path=el_image_path,
                detection_origin=detection_origin,
                **kwargs,
            )

        for layout_element, element in translation_mapping:
            if hasattr(layout_element, "parent") and layout_element.parent is not None:
                element_parent = first(
                    (el for l_el, el in translation_mapping if l_el is layout_element.parent),
                )
                element.metadata.parent_id = element_parent.id
        sorted_page_elements = page_elements
        if sortable and sort_mode != SORT_MODE_DONT:
            sorted_page_elements = sort_page_elements(page_elements, sort_mode)

        if include_page_breaks and i < num_pages - 1:
            sorted_page_elements.append(PageBreak(text=""))
        elements.extend(sorted_page_elements)

    return elements
