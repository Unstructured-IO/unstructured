from __future__ import annotations

import numbers
import subprocess
from io import BufferedReader, BytesIO, TextIOWrapper
from tempfile import SpooledTemporaryFile
from time import sleep
from typing import IO, TYPE_CHECKING, Any, Optional, TypeVar, cast

import emoji
import psutil

from unstructured.documents.coordinates import CoordinateSystem, PixelSpace
from unstructured.documents.elements import (
    TYPE_TO_TEXT_ELEMENT_MAP,
    CheckBox,
    CoordinatesMetadata,
    Element,
    ElementMetadata,
    ElementType,
    ListItem,
    PageBreak,
    Text,
)
from unstructured.logger import logger
from unstructured.nlp.patterns import ENUMERATED_BULLETS_RE, UNICODE_BULLETS_RE

if TYPE_CHECKING:
    from unstructured_inference.inference.layout import PageLayout
    from unstructured_inference.inference.layoutelement import LayoutElement


def normalize_layout_element(
    layout_element: LayoutElement | Element | dict[str, Any],
    coordinate_system: Optional[CoordinateSystem] = None,
    infer_list_items: bool = True,
    source_format: Optional[str] = "html",
) -> Element | list[Element]:
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

    text = layout_dict.get("text", "")
    # Both `coordinates` and `coordinate_system` must be present
    # in order to add coordinates metadata to the element.
    coordinates = layout_dict.get("coordinates") if coordinate_system else None
    element_type = layout_dict.get("type")
    prob = layout_dict.get("prob")
    aux_origin = layout_dict.get("source", None)
    origin = None
    if aux_origin:
        origin = aux_origin.value
    if prob and isinstance(prob, (int, str, float, numbers.Number)):
        class_prob_metadata = ElementMetadata(detection_class_prob=float(prob))  # type: ignore
    else:
        class_prob_metadata = ElementMetadata()
    common_kwargs = {
        "coordinates": coordinates,
        "coordinate_system": coordinate_system,
        "metadata": class_prob_metadata,
        "detection_origin": origin,
    }
    if element_type == ElementType.LIST:
        if infer_list_items:
            return layout_list_to_list_items(
                text,
                **common_kwargs,
            )
        else:
            return ListItem(
                text=text,
                **common_kwargs,
            )

    elif element_type in TYPE_TO_TEXT_ELEMENT_MAP:
        assert isinstance(element_type, str)  # Added to resolve type-error
        _element_class = TYPE_TO_TEXT_ELEMENT_MAP[element_type]
        _element_class = _element_class(
            text=text,
            **common_kwargs,
        )
        if element_type == ElementType.HEADLINE:
            _element_class.metadata.category_depth = 1
        elif element_type == ElementType.SUB_HEADLINE:
            _element_class.metadata.category_depth = 2
        return _element_class
    elif element_type in [
        ElementType.CHECK_BOX_CHECKED,
        ElementType.CHECK_BOX_UNCHECKED,
        ElementType.RADIO_BUTTON_CHECKED,
        ElementType.RADIO_BUTTON_UNCHECKED,
        ElementType.CHECKED,
        ElementType.UNCHECKED,
    ]:
        checked = element_type in [
            ElementType.CHECK_BOX_CHECKED,
            ElementType.RADIO_BUTTON_CHECKED,
            ElementType.CHECKED,
        ]
        return CheckBox(
            checked=checked,
            **common_kwargs,
        )
    else:
        return Text(
            text=text,
            **common_kwargs,
        )


def layout_list_to_list_items(
    text: Optional[str],
    coordinates: Optional[tuple[tuple[float, float], ...]],
    coordinate_system: Optional[CoordinateSystem],
    metadata: Optional[ElementMetadata],
    detection_origin: Optional[str],
) -> list[Element]:
    """Converts a list LayoutElement to a list of ListItem elements."""
    split_items = ENUMERATED_BULLETS_RE.split(text) if text else []
    # NOTE(robinson) - this means there wasn't a match for the enumerated bullets
    if len(split_items) == 1:
        split_items = UNICODE_BULLETS_RE.split(text) if text else []

    list_items: list[Element] = []
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


def add_element_metadata(
    element: Element,
    filename: Optional[str] = None,
    filetype: Optional[str] = None,
    page_number: Optional[int] = None,
    url: Optional[str] = None,
    text_as_html: Optional[str] = None,
    coordinates: Optional[tuple[tuple[float, float], ...]] = None,
    coordinate_system: Optional[CoordinateSystem] = None,
    image_path: Optional[str] = None,
    detection_origin: Optional[str] = None,
    languages: Optional[list[str]] = None,
    **kwargs: Any,
) -> Element:
    """Adds document metadata to the document element.

    Document metadata includes information like the filename, source url, and page number.
    """

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
    link_start_indexes = [link.get("start_index") for link in links] if links else None
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
        link_start_indexes=link_start_indexes,
        emphasized_text_contents=emphasized_text_contents,
        emphasized_text_tags=emphasized_text_tags,
        category_depth=depth,
        image_path=image_path,
        languages=languages,
    )
    element.metadata.update(metadata)
    if detection_origin is not None:
        element.metadata.detection_origin = detection_origin
    return element


def remove_element_metadata(layout_elements: list[Element]) -> list[Element]:
    """Removes document metadata from the document element.

    Document metadata includes information like the filename, source url, and page number.
    """
    elements: list[Element] = []
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


def _is_soffice_running():
    for proc in psutil.process_iter():
        try:
            if "soffice" in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def convert_office_doc(
    input_filename: str,
    output_directory: str,
    target_format: str = "docx",
    target_filter: Optional[str] = None,
    wait_for_soffice_ready_time_out: int = 10,
):
    """Converts a .doc/.ppt file to a .docx/.pptx file using the libreoffice CLI.

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
    wait_for_soffice_ready_time_out: int
        The max wait time in seconds for soffice to become available to run

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
        # only one soffice process can be ran
        wait_time = 0
        sleep_time = 0.1
        output = subprocess.run(command, capture_output=True)
        message = output.stdout.decode().strip()
        # we can't rely on returncode unfortunately because on macOS it would return 0 even when the
        # command failed to run; instead we have to rely on the stdout being empty as a sign of the
        # process failed
        while (wait_time < wait_for_soffice_ready_time_out) and (message == ""):
            wait_time += sleep_time
            if _is_soffice_running():
                sleep(sleep_time)
            else:
                output = subprocess.run(command, capture_output=True)
                message = output.stdout.decode().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            """soffice command was not found. Please install libreoffice
on your system and try again.

- Install instructions: https://www.libreoffice.org/get-help/install-howto/
- Mac: https://formulae.brew.sh/cask/libreoffice
- Debian: https://wiki.debian.org/LibreOffice""",
        )

    logger.info(message)
    if output.returncode != 0 or message == "":
        logger.error(
            "soffice failed to convert to format %s with code %i", target_format, output.returncode
        )
        logger.error(output.stderr.decode().strip())


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


_T = TypeVar("_T")


def spooled_to_bytes_io_if_needed(file: _T | SpooledTemporaryFile[bytes]) -> _T | BytesIO:
    """Convert `file` to `BytesIO` when it is a `SpooledTemporaryFile`.

    Note that `file` does not need to be IO[bytes]. It can be `None` or `bytes` and this function
    will not complain.

    In Python <3.11, `SpooledTemporaryFile` does not implement `.readable()` or `.seekable()` which
    triggers an exception when the file is loaded by certain packages. In particular, the stdlib
    `zipfile.Zipfile` raises on opening a `SpooledTemporaryFile` as does `Pandas.read_csv()`.
    """
    if isinstance(file, SpooledTemporaryFile):
        file.seek(0)
        return BytesIO(cast(bytes, file.read()))

    # -- return `file` unchanged otherwise --
    return file


def convert_to_bytes(file: bytes | IO[bytes]) -> bytes:
    """Extract the bytes from `file` without preventing it from being read again later.

    As a convenience to simplify client code, also returns `file` unchanged if it is already bytes.
    """
    if isinstance(file, bytes):
        return file

    if isinstance(file, SpooledTemporaryFile):
        file.seek(0)
        f_bytes = file.read()
        file.seek(0)
        return f_bytes

    if isinstance(file, BytesIO):
        return file.getvalue()

    if isinstance(file, (TextIOWrapper, BufferedReader)):
        with open(file.name, "rb") as f:
            return f.read()

    raise ValueError("Invalid file-like object type")


def contains_emoji(s: str) -> bool:
    """
    Check if the input string contains any emoji characters.

    Parameters:
    - s (str): The input string to check.

    Returns:
    - bool: True if the string contains any emoji, False otherwise.
    """

    return bool(emoji.emoji_count(s))


def get_page_image_metadata(page: PageLayout) -> dict[str, Any]:
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


def ocr_data_to_elements(
    ocr_data: list["LayoutElement"],
    image_size: tuple[int | float, int | float],
    common_metadata: Optional[ElementMetadata] = None,
    infer_list_items: bool = True,
    source_format: Optional[str] = None,
) -> list[Element]:
    """Convert OCR layout data into `unstructured` elements with associated metadata."""

    image_width, image_height = image_size
    coordinate_system = PixelSpace(width=image_width, height=image_height)
    elements: list[Element] = []
    for layout_element in ocr_data:
        element = normalize_layout_element(
            layout_element,
            coordinate_system=coordinate_system,
            infer_list_items=infer_list_items,
            source_format=source_format if source_format else "html",
        )

        if common_metadata:
            element.metadata.update(common_metadata)

        elements.append(element)

    return elements
