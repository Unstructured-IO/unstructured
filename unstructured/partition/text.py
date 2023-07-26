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
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)


def _split_in_half_at_breakpoint(
    content: str,
    breakpoint: str = " ",
) -> List[str]:
    """Splits a segment of content at the breakpoint closest to the middle"""
    mid = len(content) // 2
    for i in range(len(content) // 2):
        if content[mid + i] == breakpoint:
            mid += i
            break
        elif content[mid - i] == breakpoint:
            mid += -i
            break

    return [content[:mid].rstrip(), content[mid:].lstrip()]


def _split_content_size_n(content: str, n: int) -> List[str]:
    """Splits a section of content into chunks that are at most
    size n without breaking apart words."""
    segments = []
    if len(content) < n * 2:
        segments = list(_split_in_half_at_breakpoint(content))
    else:
        segments = textwrap.wrap(content, width=n)
    return segments


def split_content_to_fit_max(
    content: str,
    max_partition: Optional[int] = 1500,
) -> List[str]:
    """Splits a paragraph or section of content so that all of the elements fit into the
    max partition window."""
    sentences = sent_tokenize(content)
    chunks = []
    tmp_chunk = ""
    for sentence in sentences:
        if max_partition is not None and len(sentence) > max_partition:
            if tmp_chunk:
                chunks.append(tmp_chunk)
                tmp_chunk = ""
            segments = _split_content_size_n(sentence, n=max_partition)
            chunks.extend(segments[:-1])
            tmp_chunk = segments[-1]
        else:
            if max_partition is not None and len(tmp_chunk + " " + sentence) > max_partition:
                chunks.append(tmp_chunk)
                tmp_chunk = sentence
            else:
                if not tmp_chunk:
                    tmp_chunk = sentence
                else:
                    tmp_chunk += " " + sentence
                    tmp_chunk = tmp_chunk.strip()
    if tmp_chunk:
        chunks.append(tmp_chunk)

    return chunks


def combine_paragraphs_less_than_min(
    split_paragraphs: List[str],
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
) -> List[str]:
    """Combine paragraphs less than `min_partition` while not exceeding `max_partition`."""
    if type(split_paragraphs) is not list:
        raise ValueError("`split_paragraphs` is not a list")
    file_content: List[str] = []
    tmp_paragraph = ""
    next_index = 0
    for current_index, paragraph in enumerate(split_paragraphs):
        if next_index > current_index:
            continue  # Skip the current iteration if `next_index`` is already updated
        if min_partition is not None and len(paragraph) < min_partition:
            # Combine paragraphs that are less than `min_partition``
            # while not exceeding `max_partition``
            tmp_paragraph += paragraph + "\n"

            while len(tmp_paragraph.strip()) < min_partition:
                if current_index + 1 == len(split_paragraphs):
                    # If it's the last paragraph, append the paragraph
                    # to the previous content
                    file_content[-1] += " " + tmp_paragraph.rstrip()
                    tmp_paragraph = ""
                    break
                for offset_index, para in enumerate(
                    split_paragraphs[current_index + 1 :], start=1  # noqa
                ):
                    if (
                        max_partition is not None
                        and len(tmp_paragraph + "\n" + para) < max_partition
                    ):
                        tmp_paragraph += "\n" + para
                        # Update `next_index` to skip already combined paragraphs
                        next_index = offset_index + current_index + 1

                    if len(tmp_paragraph.strip()) > min_partition:
                        break  # Stop combining if the combined paragraphs
                        # meet the `min_partition`` requirement
                    elif (
                        max_partition is not None
                        and len(tmp_paragraph) < min_partition
                        and len(tmp_paragraph + "\n" + para) > max_partition
                    ):
                        raise ValueError(
                            "`min_partition` and `max_partition` are defined too close together",
                        )
            # Add the combined paragraph to the final result
            file_content.append(
                tmp_paragraph.strip(),
            )
            tmp_paragraph = ""
        else:
            file_content.append(paragraph)
    return file_content


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
    metadata_date: Optional[str] = None,
    **kwargs,
) -> List[Element]:
    """Partitions an .txt documents into its constituent paragraph elements.
    If paragraphs are below "min_partition" or above "max_partition" boundaries,
    they are combined or split.
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
    metadata_date
        The day of the last modification
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

    last_modification_date = None
    if filename is not None:
        encoding, file_text = read_txt_file(filename=filename, encoding=encoding)
        last_modification_date = get_last_modified_date(filename)

    elif file is not None:
        encoding, file_text = read_txt_file(file=file, encoding=encoding)
        last_modification_date = get_last_modified_date_from_file(file)

    elif text is not None:
        file_text = str(text)

    if paragraph_grouper is False:
        pass
    elif paragraph_grouper is not None:
        file_text = paragraph_grouper(file_text)
    else:
        file_text = group_broken_paragraphs(file_text)

    if min_partition is not None and len(file_text) < min_partition:
        raise ValueError("`min_partition` cannot be larger than the length of file contents.")

    split_paragraphs = re.split(PARAGRAPH_PATTERN, file_text.strip())

    paragraphs = combine_paragraphs_less_than_min(
        split_paragraphs=split_paragraphs,
        max_partition=max_partition,
        min_partition=min_partition,
    )

    file_content = []

    for paragraph in paragraphs:
        file_content.extend(
            split_content_to_fit_max(
                content=paragraph,
                max_partition=max_partition,
            ),
        )

    elements: List[Element] = []
    metadata = (
        ElementMetadata(
            filename=metadata_filename or filename,
            date=metadata_date or last_modification_date,
        )
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
        return Address(
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
