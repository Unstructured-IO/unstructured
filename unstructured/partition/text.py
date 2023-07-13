import re
import textwrap
from typing import IO, Callable, List, Optional, Tuple

from unstructured.cleaners.core import clean_bullets, group_broken_paragraphs
from unstructured.documents.coordinates import CoordinateSystem
from unstructured.documents.elements import (
    Address,
    Element,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Text,
    Title,
    process_metadata,
)
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.nlp.patterns import PARAGRAPH_PATTERN
from unstructured.nlp.tokenize import sent_tokenize
from unstructured.partition.common import exactly_one
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)


def split_by_paragraph(
    content: str,
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
) -> List[str]:
    # import pdb;pdb.set_trace()
    paragraphs = re.split(PARAGRAPH_PATTERN, content)
    if max_partition is None:
        return paragraphs

    split_paragraphs = []
    for paragraph in paragraphs:
        split_paragraphs.extend(
            _split_content_to_fit_min_max(
                paragraph,
                max_partition=max_partition,
                min_partition=min_partition,
            ),
        )
    return split_paragraphs


def _split_content_size_n(content: str, n: int) -> List[str]:
    """Splits a string into chunks that are at most size n without breaking apart words."""
    segments = []
    if len(content) < n * 2:
        segments = list(split_content_in_half(content))
    else:
        segments = textwrap.wrap(content, width=n)
    return segments


def split_content_in_half(content: str) -> Tuple[str, str]:
    """Splits a string in half without breaking apart words."""
    mid = len(content) // 2
    left = content[:mid].rstrip()
    right = content[mid:].lstrip()
    if not right or content[mid] == " ":
        return left, right
    elif not left or content[mid - 1] == " ":
        return left.rstrip(), right.lstrip()
    else:
        i = mid
        while content[i] != " ":
            i += 1
        return content[:i].rstrip(), content[i:].lstrip()


def _split_content_to_fit_min_max(
    content: str,
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
) -> List[str]:
    """Splits a section of content so that all of the elements fit into the
    max/min partition window."""
    sentences = sent_tokenize(content)

    chunks = []
    tmp = ""
    for sentence in sentences:
        if max_partition is not None and len(sentence) > max_partition:
            if tmp:
                chunks.append(tmp)
                tmp = ""
            segments = _split_content_size_n(sentence, n=max_partition)
            chunks.extend(segments[:-1])
            tmp = segments[-1]
        elif (
            min_partition is not None
            and max_partition is not None
            and len(sentence) >= min_partition
        ):
            if len(tmp + " " + sentence) > max_partition:
                if len(tmp) >= min_partition:
                    chunks.append(tmp)
                    tmp = ""
                elif not tmp:
                    chunks.append(sentence)
                else:
                    chunks.extend(_split_content_size_n(tmp + " " + sentence, n=max_partition))
            else:
                if not tmp:
                    chunks.append(sentence)
                else:
                    chunks.extend([tmp, sentence])
                    tmp = ""
        else:
            tmp += " " + sentence
            tmp = tmp.strip()

    if tmp:
        chunks.append(tmp)

    return chunks


@process_metadata()
@add_metadata_with_filetype(FileType.TXT)
def partition_text(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    encoding: Optional[str] = None,
    paragraph_grouper: Optional[Callable[[str], str]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
    **kwargs,
) -> List[Element]:
    """Partitions an .txt documents into its constituent elements.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "r" mode --> open(filename, "r").
    text
        The string representation of the .txt document.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    paragrapher_grouper
        A str -> str function for fixing paragraphs that are interrupted by line breaks
        for formatting purposes.
    include_metadata
        Determines whether or not metadata is included in the output.
    max_partition
        The maximum number of characters to include in a partition. If None is passed,
        no maximum is applied.
    min_partition
        The minimum number of characters to include in a partition.
    """
    if text is not None and text.strip() == "" and not file and not filename:
        return []

    if (
        min_partition is not None
        and max_partition is not None
        and (min_partition > max_partition or min_partition < 0 or max_partition < 0)
    ):
        raise ValueError("Invalid values for min_partition and/or max_partition.")

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file, text=text)

    if filename is not None:
        encoding, file_text = read_txt_file(filename=filename, encoding=encoding)

    elif file is not None:
        encoding, file_text = read_txt_file(file=file, encoding=encoding)

    elif text is not None:
        file_text = str(text)

    if paragraph_grouper is not None:
        file_text = paragraph_grouper(file_text)
    else:
        file_text = group_broken_paragraphs(file_text)

    file_content = split_by_paragraph(
        file_text,
        max_partition=max_partition,
        min_partition=min_partition,
    )

    elements: List[Element] = []
    metadata = (
        ElementMetadata(filename=metadata_filename or filename)
        if include_metadata
        else ElementMetadata()
    )
    for ctext in file_content:
        ctext = ctext.strip()

        if ctext:
            element = element_from_text(ctext)
            element.metadata = metadata
            elements.append(element)

    return elements


def element_from_text(
    text: str,
    coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
    coordinate_system: Optional[CoordinateSystem] = None,
) -> Element:
    if is_bulleted_text(text):
        return ListItem(
            text=clean_bullets(text),
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )
    elif is_us_city_state_zip(text):
        return Address(text=text, coordinates=coordinates, coordinate_system=coordinate_system)
    elif is_possible_narrative_text(text):
        return NarrativeText(
            text=text,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )
    elif is_possible_title(text):
        return Title(text=text, coordinates=coordinates, coordinate_system=coordinate_system)
    else:
        return Text(text=text, coordinates=coordinates, coordinate_system=coordinate_system)
