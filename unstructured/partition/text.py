import copy
import re
import textwrap
from typing import IO, Any, Callable, List, Optional, Tuple

from unstructured.chunking.title import add_chunking_strategy
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
from unstructured.nlp.patterns import PARAGRAPH_PATTERN, UNICODE_BULLETS_RE
from unstructured.nlp.tokenize import sent_tokenize
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.lang import apply_lang_metadata
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_email_address,
    is_possible_narrative_text,
    is_possible_numbered_list,
    is_possible_title,
    is_us_city_state_zip,
)


def partition_text(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    encoding: Optional[str] = None,
    paragraph_grouper: Optional[Callable[[str], str]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    languages: Optional[List[str]] = ["auto"],
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    detect_language_per_element: bool = False,
    detection_origin: Optional[str] = "text",
    **kwargs: Any,
) -> List[Element]:
    """Partitions an .txt documents into its constituent paragraph elements.
    If paragraphs are below "min_partition" or above "max_partition" boundaries,
    they are combined or split.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    text
        The string representation of the .txt document.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    paragrapher_grouper
        A str -> str function for fixing paragraphs that are interrupted by line breaks
        for formatting purposes.
    include_metadata
        Determines whether or not metadata is included in the output.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    max_partition
        The maximum number of characters to include in a partition. If None is passed,
        no maximum is applied.
    min_partition
        The minimum number of characters to include in a partition.
    metadata_last_modified
        The day of the last modification
    """
    return _partition_text(
        filename=filename,
        file=file,
        text=text,
        encoding=encoding,
        paragraph_grouper=paragraph_grouper,
        metadata_filename=metadata_filename,
        include_metadata=include_metadata,
        languages=languages,
        max_partition=max_partition,
        min_partition=min_partition,
        metadata_last_modified=metadata_last_modified,
        chunking_strategy=chunking_strategy,
        detect_language_per_element=detect_language_per_element,
        detection_origin=detection_origin,
        **kwargs,
    )


@process_metadata()
@add_metadata_with_filetype(FileType.TXT)
@add_chunking_strategy()
def _partition_text(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    encoding: Optional[str] = None,
    paragraph_grouper: Optional[Callable[[str], str]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    languages: Optional[List[str]] = ["auto"],
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    detect_language_per_element: bool = False,
    detection_origin: Optional[str] = "text",
    **kwargs: Any,
) -> List[Element]:
    """internal API for `partition_text`"""
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
    file_text = ""

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

    file_content = _split_by_paragraph(
        file_text,
        min_partition=min_partition,
        max_partition=max_partition,
    )

    elements: List[Element] = []
    if include_metadata:
        metadata = ElementMetadata(
            filename=metadata_filename or filename,
            last_modified=metadata_last_modified or last_modification_date,
            languages=languages,
        )
        metadata.detection_origin = detection_origin
    else:
        metadata = ElementMetadata()

    for ctext in file_content:
        ctext = ctext.strip()

        if ctext and not is_empty_bullet(ctext):
            element = element_from_text(ctext)
            element.metadata = copy.deepcopy(metadata)
            elements.append(element)

    elements = list(
        apply_lang_metadata(
            elements=elements,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
        ),
    )
    return elements


def is_empty_bullet(text: str) -> bool:
    """Checks if input text is an empty bullet."""
    return UNICODE_BULLETS_RE.match(text) and len(text) == 1


def element_from_text(
    text: str,
    coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
    coordinate_system: Optional[CoordinateSystem] = None,
) -> Element:
    if is_bulleted_text(text):
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


def _combine_paragraphs_less_than_min(
    split_paragraphs: List[str],
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
) -> List[str]:
    """Combine paragraphs less than `min_partition` while not exceeding `max_partition`."""
    min_partition = min_partition or 0
    max_possible_partition = len(" ".join(split_paragraphs))
    max_partition = max_partition or max_possible_partition

    combined_paras: List[str] = []
    combined_idxs: List[int] = []
    for i, para in enumerate(split_paragraphs):
        if i in combined_idxs:
            continue
        # Paragraphs have already been split to fit `max_partition`, so they can be safely added
        # to the final list of chunks if they are also greater than `min_partition`
        if len(para) >= min_partition:
            combined_paras.append(para)
        else:
            combined_para = para
            for j, next_para in enumerate(split_paragraphs[i + 1 :]):  # noqa
                # Combine the current paragraph(s), e.g. `combined_para` with the next paragraph(s)
                # as long as they don't exceed `max_partition`, and keep track of the indices
                # that have been combined.
                if len(combined_para) + len(next_para) + 1 <= max_partition:
                    combined_idxs.append(i + j + 1)
                    combined_para += " " + next_para
                else:
                    break
            combined_paras.append(combined_para)

    return combined_paras


def _split_by_paragraph(
    file_text: str,
    min_partition: Optional[int] = 0,
    max_partition: Optional[int] = 1500,
) -> List[str]:
    """Split text into paragraphs that fit within the `min_` and `max_partition` window."""
    paragraphs = re.split(PARAGRAPH_PATTERN, file_text.strip())

    split_paragraphs: List[str] = []
    for paragraph in paragraphs:
        split_paragraphs.extend(
            _split_content_to_fit_max(
                content=paragraph,
                max_partition=max_partition,
            ),
        )

    combined_paragraphs = _combine_paragraphs_less_than_min(
        split_paragraphs=split_paragraphs,
        max_partition=max_partition,
        min_partition=min_partition,
    )

    return combined_paragraphs


def _split_content_size_n(content: str, n: int) -> List[str]:
    """Splits a section of content into chunks that are at most
    size n without breaking apart words."""
    segments = []
    if len(content) < n * 2:
        segments = list(_split_in_half_at_breakpoint(content))
    else:
        segments = textwrap.wrap(content, width=n)
    return segments


def _split_content_to_fit_max(
    content: str,
    max_partition: Optional[int] = 1500,
) -> List[str]:
    """Splits a paragraph or section of content so that all of the elements fit into the
    max partition window."""
    sentences = sent_tokenize(content)
    chunks: List[str] = []
    tmp_chunk = ""
    # Initialize an empty string to collect sentence segments (`tmp_chunk`).
    for sentence in sentences:
        # If a single sentence is larger than `max_partition`, the sentence will be split by
        # `_split_content_size_n` and the last segment of the original sentence will be used
        # as the beginning of the next chunk.
        if max_partition is not None and len(sentence) > max_partition:
            if tmp_chunk:
                chunks.append(tmp_chunk)
                tmp_chunk = ""
            segments = _split_content_size_n(sentence, n=max_partition)
            chunks.extend(segments[:-1])
            tmp_chunk = segments[-1]
        else:
            # If the current sentence is smaller than `max_partition`, but adding it to the
            # current `tmp_chunk` would exceed `max_partition`, add the `tmp_chunk` to the
            # final list of `chunks` and begin the next chunk with the current sentence.
            if max_partition is not None and len(tmp_chunk + " " + sentence) > max_partition:
                chunks.append(tmp_chunk)
                tmp_chunk = sentence
            else:
                # Otherwise, the sentence can be added to `tmp_chunk`
                if not tmp_chunk:
                    tmp_chunk = sentence
                else:
                    tmp_chunk += " " + sentence
                    tmp_chunk = tmp_chunk.strip()
    if tmp_chunk:
        chunks.append(tmp_chunk)

    return chunks


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
