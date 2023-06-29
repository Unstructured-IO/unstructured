import re
from typing import IO, Callable, List, Optional

from unstructured.cleaners.core import clean_bullets, group_broken_paragraphs
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


def split_by_paragraph(content: str, max_partition: Optional[int] = 1500) -> List[str]:
    paragraphs = re.split(PARAGRAPH_PATTERN, content)
    if max_partition is None:
        return paragraphs

    split_paragraphs = []
    for paragraph in paragraphs:
        split_paragraphs.extend(
            _split_to_fit_max_content(paragraph, max_partition=max_partition),
        )
    return split_paragraphs


def _split_content_size_n(content: str, n: int) -> List[str]:
    """Splits a string into chunks that are at most size n."""
    segments = []
    for i in range(0, len(content), n):
        segment = content[i : i + n]  # noqa: E203
        segments.append(segment)
    return segments


def _split_to_fit_max_content(content: str, max_partition: int = 1500) -> List[str]:
    """Splits a section of content so that all of the elements fit into the
    max partition window."""
    sentences = sent_tokenize(content)
    num_sentences = len(sentences)

    chunks = []
    chunk = ""

    for i, sentence in enumerate(sentences):
        if len(sentence) > max_partition:
            chunks.extend(_split_content_size_n(sentence, n=max_partition))

        if len(chunk + " " + sentence) > max_partition:
            chunks.append(chunk)
            chunk = sentence
        else:
            chunk += " " + sentence
            if i == num_sentences - 1:
                chunks.append(chunk)

    return chunks


@process_metadata()
@add_metadata_with_filetype(FileType.TXT)
def partition_text(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    encoding: Optional[str] = None,
    paragraph_grouper: Optional[Callable[[str], str]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    max_partition: Optional[int] = 1500,
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
    """
    if text is not None and text.strip() == "" and not file and not filename:
        return []

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

    file_content = split_by_paragraph(file_text, max_partition=max_partition)

    metadata_filename = metadata_filename or filename

    elements: List[Element] = []
    metadata = (
        ElementMetadata(filename=metadata_filename) if include_metadata else ElementMetadata()
    )
    for ctext in file_content:
        ctext = ctext.strip()

        if ctext:
            element = element_from_text(ctext)
            element.metadata = metadata
            elements.append(element)

    return elements


def element_from_text(text: str) -> Element:
    if is_bulleted_text(text):
        return ListItem(text=clean_bullets(text))
    elif is_us_city_state_zip(text):
        return Address(text=text)
    elif is_possible_narrative_text(text):
        return NarrativeText(text=text)
    elif is_possible_title(text):
        return Title(text=text)
    else:
        return Text(text=text)
