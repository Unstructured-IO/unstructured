import os
import tempfile
from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

import docx
import pypandoc
from docx.oxml.shared import qn
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from unstructured.cleaners.core import clean_bullets
from unstructured.documents.elements import (
    Address,
    Element,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
)
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    convert_ms_office_table_to_text,
    exactly_one,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)

# NOTE(robinson) - documentation on built in styles can be found at the link below
# ref: https://python-docx.readthedocs.io/en/latest/user/
#   styles-understanding.html#paragraph-styles-in-default-template
STYLE_TO_ELEMENT_MAPPING = {
    "Caption": Text,  # TODO(robinson) - add caption element type
    "Heading 1": Title,
    "Heading 2": Title,
    "Heading 3": Title,
    "Heading 4": Title,
    "Heading 5": Title,
    "Heading 6": Title,
    "Heading 7": Title,
    "Heading 8": Title,
    "Heading 9": Title,
    "Intense Quote": Text,  # TODO(robinson) - add quote element type
    "List": ListItem,
    "List 2": ListItem,
    "List 3": ListItem,
    "List Bullet": ListItem,
    "List Bullet 2": ListItem,
    "List Bullet 3": ListItem,
    "List Continue": ListItem,
    "List Continue 2": ListItem,
    "List Continue 3": ListItem,
    "List Number": ListItem,
    "List Number 2": ListItem,
    "List Number 3": ListItem,
    "List Paragraph": ListItem,
    "Macro Text": Text,
    "No Spacing": Text,
    "Quote": Text,  # TODO(robinson) - add quote element type
    "Subtitle": Title,
    "TOCHeading": Title,
    "Title": Title,
}


def _get_paragraph_runs(paragraph):
    """
    Get hyperlink text from a paragraph object.
    Without this, the default runs function skips over hyperlinks.

    Args:
        paragraph (Paragraph): A Paragraph object.

    Returns:
        list: A list of Run objects.
    """

    # Recursively get runs.
    def _get_runs(node, parent):
        for child in node:
            # If the child is a run, yield a Run object
            if child.tag == qn("w:r"):
                yield Run(child, parent)
            # If the child is a hyperlink, search for runs within it recursively
            if child.tag == qn("w:hyperlink"):
                yield from _get_runs(child, parent)

    return list(_get_runs(paragraph._element, paragraph))


# Add the runs property to the Paragraph class
Paragraph.runs = property(lambda self: _get_paragraph_runs(self))


@add_metadata_with_filetype(FileType.DOCX)
def partition_docx(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
) -> List[Element]:
    """Partitions Microsoft Word Documents in .docx format into its document elements.

    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_filename
        The filename to use for the metadata. Relevant because partition_doc converts the
        document to .docx before partition. We want the original source filename in the
        metadata.
    """

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file)

    if filename is not None:
        document = docx.Document(filename)
    elif file is not None:
        document = docx.Document(
            spooled_to_bytes_io_if_needed(cast(Union[BinaryIO, SpooledTemporaryFile], file)),
        )

    metadata_filename = metadata_filename or filename
    elements: List[Element] = []
    table_index = 0

    for element_item in document.element.body:
        if element_item.tag.endswith("tbl"):
            table = document.tables[table_index]
            html_table = convert_ms_office_table_to_text(table, as_html=True)
            text_table = convert_ms_office_table_to_text(table, as_html=False)
            element = Table(text_table)
            if element is not None:
                element.metadata = ElementMetadata(
                    text_as_html=html_table,
                    filename=metadata_filename,
                )
                elements.append(element)
            table_index += 1
        elif element_item.tag.endswith("p"):
            paragraph = docx.text.paragraph.Paragraph(element_item, document)
            para_element: Optional[Text] = _paragraph_to_element(paragraph)
            if para_element is not None:
                para_element.metadata = ElementMetadata(filename=metadata_filename)
                elements.append(para_element)

    return elements


def _paragraph_to_element(paragraph: docx.text.paragraph.Paragraph) -> Optional[Text]:
    """Converts a docx Paragraph object into the appropriate unstructured document element.
    If the paragraph style is "Normal" or unknown, we try to predict the element type from the
    raw text."""
    text = paragraph.text
    style_name = paragraph.style and paragraph.style.name  # .style can be None

    if len(text.strip()) == 0:
        return None

    element_class = STYLE_TO_ELEMENT_MAPPING.get(style_name)

    # NOTE(robinson) - The "Normal" style name will return None since it's in the mapping.
    # Unknown style names will also return None
    if element_class is None:
        return _text_to_element(text)
    else:
        return element_class(text)


def _text_to_element(text: str) -> Optional[Text]:
    """Converts raw text into an unstructured Text element."""
    if is_bulleted_text(text):
        clean_text = clean_bullets(text).strip()
        return ListItem(text=clean_bullets(text)) if clean_text else None

    elif is_us_city_state_zip(text):
        return Address(text=text)

    if len(text) < 2:
        return None
    elif is_possible_narrative_text(text):
        return NarrativeText(text)
    elif is_possible_title(text):
        return Title(text)
    else:
        return Text(text)


def convert_and_partition_docx(
    source_format: str,
    filename: Optional[str] = None,
    file: Optional[IO] = None,
) -> List[Element]:
    """Converts a document to DOCX and then partitions it using partition_html. Works with
    any file format support by pandoc.

    Parameters
    ----------
    source_format
        The format of the source document, .e.g. odt
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    """
    if filename is None:
        filename = ""
    exactly_one(filename=filename, file=file)

    if len(filename) > 0:
        _, filename_no_path = os.path.split(os.path.abspath(filename))
        base_filename, _ = os.path.splitext(filename_no_path)
        if not os.path.exists(filename):
            raise ValueError(f"The file {filename} does not exist.")
    elif file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        filename = tmp.name
        _, filename_no_path = os.path.split(os.path.abspath(tmp.name))

    base_filename, _ = os.path.splitext(filename_no_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_filename = os.path.join(tmpdir, f"{base_filename}.docx")
        pypandoc.convert_file(filename, "docx", format=source_format, outputfile=docx_filename)
        elements = partition_docx(filename=docx_filename, metadata_filename=filename)

    return elements
