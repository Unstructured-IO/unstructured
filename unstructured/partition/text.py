from __future__ import annotations

import copy
import re
from typing import IO, Any, Callable, Literal

from unstructured.chunking import add_chunking_strategy
from unstructured.cleaners.core import (
    auto_paragraph_grouper,
    clean_bullets,
)
from unstructured.documents.coordinates import CoordinateSystem
from unstructured.documents.elements import (
    Address,
    Element,
    ElementMetadata,
    EmailAddress,
    Footer,
    Header,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.model import FileType
from unstructured.nlp.patterns import PARAGRAPH_PATTERN, UNICODE_BULLETS_RE
from unstructured.partition.common.common import exactly_one
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_email_address,
    is_possible_narrative_text,
    is_possible_numbered_list,
    is_possible_title,
    is_us_city_state_zip,
)


@apply_metadata(FileType.TXT)
@add_chunking_strategy
def partition_text(
    filename: str | None = None,
    *,
    file: IO[bytes] | None = None,
    encoding: str | None = None,
    text: str | None = None,
    paragraph_grouper: Callable[[str], str] | Literal[False] | None = None,
    detection_origin: str | None = "text",
    **kwargs: Any,
) -> list[Element]:
    """Partition a .txt documents into its constituent paragraph elements.

    If paragraphs are below "min_partition" or above "max_partition" boundaries,
    they are combined or split.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    encoding
        The encoding method used to decode the input bytes when drawn from `filename` or `file`.
        Defaults to "utf-8".
    text
        The string representation of the .txt document.
    paragrapher_grouper
        A str -> str function for fixing paragraphs that are interrupted by line breaks
        for formatting purposes.
    """
    if text is not None and text.strip() == "" and not file and not filename:
        return []

    # -- Verify that only one of the arguments was provided --
    exactly_one(filename=filename, file=file, text=text)

    file_text = ""
    if filename is not None:
        encoding, file_text = read_txt_file(filename=filename, encoding=encoding)
    elif file is not None:
        encoding, file_text = read_txt_file(file=file, encoding=encoding)
    elif text is not None:
        file_text = str(text)

    if paragraph_grouper is False:
        pass
    elif paragraph_grouper is not None:
        file_text = paragraph_grouper(file_text)
    else:
        file_text = auto_paragraph_grouper(file_text)

    file_content = _split_by_paragraph(file_text)

    elements: list[Element] = []
    metadata = ElementMetadata(
        last_modified=get_last_modified_date(filename) if filename else None,
    )
    metadata.detection_origin = detection_origin

    for ctext in file_content:
        ctext = ctext.strip()

        if ctext and not _is_empty_bullet(ctext):
            element = element_from_text(ctext)
            element.metadata = copy.deepcopy(metadata)
            elements.append(element)

    return elements


def element_from_text(
    text: str,
    coordinates: tuple[tuple[float, float], ...] | None = None,
    coordinate_system: CoordinateSystem | None = None,
) -> Element:
    if _is_in_header_position(coordinates, coordinate_system):
        return Header(
            text=text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )
    elif _is_in_footer_position(coordinates, coordinate_system):
        return Footer(
            text=text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )
    elif is_bulleted_text(text):
        clean_text = clean_bullets(text)
        return ListItem(
            text=clean_text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )
    elif is_email_address(text):
        return EmailAddress(text=text)
    elif is_us_city_state_zip(text):
        return Address(
            text=text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )
    elif is_possible_numbered_list(text):
        return ListItem(
            text=text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )
    elif is_possible_narrative_text(text):
        return NarrativeText(
            text=text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )
    elif is_possible_title(text):
        return Title(
            text=text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )
    else:
        return Text(
            text=text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )


# ================================================================================================
# HELPER FUNCTIONS
# ================================================================================================


def _get_height_percentage(
    coordinates: tuple[tuple[float, float], ...],
    coordinate_system: CoordinateSystem,
) -> float:
    avg_y = sum(coordinate[1] for coordinate in coordinates) / len(coordinates)
    return avg_y / coordinate_system.height


def _is_empty_bullet(text: str) -> bool:
    """Checks if input text is an empty bullet."""
    return bool(UNICODE_BULLETS_RE.match(text) and len(text) == 1)


def _is_in_footer_position(
    coordinates: tuple[tuple[float, float], ...] | None,
    coordinate_system: CoordinateSystem | None,
    threshold: float = 0.93,
) -> bool:
    """Checks to see if the position of the text indicates that the text belongs
    to a footer."""
    if coordinates is None or coordinate_system is None:
        return False

    height_percentage = _get_height_percentage(coordinates, coordinate_system)
    return height_percentage > threshold


def _is_in_header_position(
    coordinates: tuple[tuple[float, float], ...] | None,
    coordinate_system: CoordinateSystem | None,
    threshold: float = 0.07,
) -> bool:
    """Checks to see if the position of the text indicates that the text belongs to a header."""
    if coordinates is None or coordinate_system is None:
        return False

    height_percentage = _get_height_percentage(coordinates, coordinate_system)
    return height_percentage < threshold


def _split_by_paragraph(file_text: str) -> list[str]:
    """Split text into paragraphs."""
    return re.split(PARAGRAPH_PATTERN, file_text.strip())
