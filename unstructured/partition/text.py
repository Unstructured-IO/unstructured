import re
import textwrap
from typing import IO, Callable, List, Optional, Tuple

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
    is_email_address,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)


def split_by_paragraph(
    file_text: str,
    min_partition: Optional[int] = 0,
    max_partition: Optional[int] = 1500,
) -> List[str]:
    paragraphs = re.split(PARAGRAPH_PATTERN, file_text.strip())

    split_paragraphs = []
    for paragraph in paragraphs:
        split_paragraphs.extend(
            split_content_to_fit_max(
                content=paragraph,
                max_partition=max_partition,
            ),
        )

    combined_paragraphs = combine_paragraphs_less_than_min(
        split_paragraphs=split_paragraphs,
        max_partition=max_partition,
        min_partition=min_partition,
    )

    return combined_paragraphs


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
    min_partition = min_partition or 0
    max_possible_partition = len(" ".join(split_paragraphs))
    max_partition = max_partition or max_possible_partition

    combined_paras = []
    combined_idxs = []
    for i, para in enumerate(split_paragraphs):
        if i in combined_idxs:
            continue

        if len(para) >= min_partition:
            combined_paras.append(para)
        else:
            combined_para = para
            for j, next_para in enumerate(split_paragraphs[i + 1 :]):  # noqa
                if len(combined_para) + len(next_para) + 1 <= max_partition:
                    combined_idxs.append(i + j + 1)
                    combined_para += " " + next_para
                else:
                    break
            combined_paras.append(combined_para)

    return combined_paras


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
    metadata_last_modified: Optional[str] = None,
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
    metadata_last_modified
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
        file_text = auto_paragraph_grouper(file_text)

    if min_partition is not None and len(file_text) < min_partition:
        raise ValueError("`min_partition` cannot be larger than the length of file contents.")

    file_content = split_by_paragraph(
        file_text,
        min_partition=min_partition,
        max_partition=max_partition,
    )

    elements: List[Element] = []
    metadata = (
        ElementMetadata(
            filename=metadata_filename or filename,
            last_modified=metadata_last_modified or last_modification_date,
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
    elif is_email_address(text):
        return EmailAddress(text=text)
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
