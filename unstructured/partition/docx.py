import os
import tempfile
from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Tuple, Union, cast

import docx
from docx.oxml.shared import qn
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from unstructured.cleaners.core import clean_bullets
from unstructured.documents.elements import (
    Address,
    Element,
    ElementMetadata,
    EmailAddress,
    Footer,
    Header,
    ListItem,
    NarrativeText,
    PageBreak,
    Table,
    Text,
    Title,
    process_metadata,
)
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    convert_ms_office_table_to_text,
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_email_address,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)
from unstructured.utils import dependency_exists

if dependency_exists("pypandoc"):
    import pypandoc

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


@process_metadata()
@add_metadata_with_filetype(FileType.DOCX)
def partition_docx(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
    include_page_breaks: bool = True,
    include_metadata: bool = True,
    metadata_last_modified: Optional[str] = None,
    **kwargs,
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
    metadata_last_modified
        The last modified date for the document.
    """

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file)

    last_modification_date = None
    if filename is not None:
        if not filename.startswith("/tmp"):
            last_modification_date = get_last_modified_date(filename)

        document = docx.Document(filename)
    elif file is not None:
        last_modification_date = get_last_modified_date_from_file(file)

        document = docx.Document(
            spooled_to_bytes_io_if_needed(
                cast(Union[BinaryIO, SpooledTemporaryFile], file),
            ),
        )

    elements: List[Element] = []
    table_index = 0

    headers_and_footers = _get_headers_and_footers(document, metadata_filename)
    if len(headers_and_footers) > 0:
        elements.extend(headers_and_footers[0][0])

    document_contains_pagebreaks = _element_contains_pagebreak(document._element)
    page_number = 1 if document_contains_pagebreaks else None
    section = 0
    is_list = False
    for element_item in document.element.body:
        if element_item.tag.endswith("tbl"):
            table = document.tables[table_index]
            emphasized_texts = _get_emphasized_texts_from_table(table)
            html_table = convert_ms_office_table_to_text(table, as_html=True)
            text_table = convert_ms_office_table_to_text(table, as_html=False)
            element = Table(text_table)
            if element is not None:
                element.metadata = ElementMetadata(
                    text_as_html=html_table,
                    filename=metadata_filename,
                    page_number=page_number,
                    last_modified=metadata_last_modified or last_modification_date,
                    emphasized_texts=emphasized_texts if emphasized_texts else None,
                )
                elements.append(element)
            table_index += 1
        elif element_item.tag.endswith("p"):
            if "<w:numPr>" in element_item.xml:
                is_list = True
            paragraph = docx.text.paragraph.Paragraph(element_item, document)
            emphasized_texts = _get_emphasized_texts_from_paragraph(paragraph)
            para_element: Optional[Text] = _paragraph_to_element(paragraph, is_list)
            if para_element is not None:
                para_element.metadata = ElementMetadata(
                    filename=metadata_filename,
                    page_number=page_number,
                    last_modified=metadata_last_modified or last_modification_date,
                    emphasized_texts=emphasized_texts if emphasized_texts else None,
                )
                elements.append(para_element)
            is_list = False
        elif element_item.tag.endswith("sectPr"):
            if len(headers_and_footers) > section:
                footers = headers_and_footers[section][1]
                elements.extend(footers)

            section += 1
            if len(headers_and_footers) > section:
                headers = headers_and_footers[section][0]
                elements.extend(headers)

        if page_number is not None and _element_contains_pagebreak(element_item):
            page_number += 1
            if include_page_breaks:
                elements.append(PageBreak(text=""))

    return elements


def _paragraph_to_element(
    paragraph: docx.text.paragraph.Paragraph,
    is_list=False,
) -> Optional[Text]:
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
    if is_list:
        return _text_to_element(text, is_list)
    elif element_class is None:
        return _text_to_element(text)
    else:
        return element_class(text)


def _element_contains_pagebreak(element) -> bool:
    """Detects if an element contains a page break. Checks for both "hard" page breaks
    (page breaks inserted by the user) and "soft" page breaks, which are sometimes
    inserted by the MS Word renderer. Note that soft page breaks aren't always present.
    Whether or not pages are tracked may depend on your Word renderer."""
    page_break_indicators = [
        ["w:br", 'type="page"'],  # "Hard" page break inserted by user
        ["lastRenderedPageBreak"],  # "Soft" page break inserted by renderer
    ]
    if hasattr(element, "xml"):
        for indicators in page_break_indicators:
            if all(indicator in element.xml for indicator in indicators):
                return True
    return False


def _text_to_element(text: str, is_list=False) -> Optional[Text]:
    """Converts raw text into an unstructured Text element."""
    if is_bulleted_text(text) or is_list:
        clean_text = clean_bullets(text).strip()
        return ListItem(text=clean_bullets(text)) if clean_text else None

    elif is_us_city_state_zip(text):
        return Address(text=text)
    elif is_email_address(text):
        return EmailAddress(text=text)
    if len(text) < 2:
        return None
    elif is_possible_narrative_text(text):
        return NarrativeText(text)
    elif is_possible_title(text):
        return Title(text)
    else:
        return Text(text)


def _join_paragraphs(paragraphs: List[docx.text.paragraph.Paragraph]) -> Optional[str]:
    return "\n".join([paragraph.text for paragraph in paragraphs])


def _get_headers_and_footers(
    document: docx.document.Document,
    metadata_filename: Optional[str],
) -> List[Tuple[List[Header], List[Footer]]]:
    headers_and_footers = []
    attr_prefixes = ["", "first_page_", "even_page_"]

    for section in document.sections:
        headers = []
        footers = []

        for _type in ["header", "footer"]:
            for prefix in attr_prefixes:
                _elem = getattr(section, f"{prefix}{_type}", None)
                if _elem is None:
                    continue

                text = _join_paragraphs(_elem.paragraphs)
                if text:
                    header_footer_type = prefix[:-1] or "primary"
                    metadata = ElementMetadata(
                        filename=metadata_filename,
                        header_footer_type=header_footer_type,
                    )

                    if _type == "header":
                        headers.append(Header(text=text, metadata=metadata))
                    elif _type == "footer":
                        footers.append(Footer(text=text, metadata=metadata))

        headers_and_footers.append((headers, footers))

    return headers_and_footers


def convert_and_partition_docx(
    source_format: str,
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
) -> List[Element]:
    """Converts a document to DOCX and then partitions it using partition_docx. Works with
    any file format support by pandoc.

    Parameters
    ----------
    source_format
        The format of the source document, .e.g. odt
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_metadata
        Determines whether or not metadata is included in the metadata attribute on the
        elements in the output.
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
        pypandoc.convert_file(
            filename,
            "docx",
            format=source_format,
            outputfile=docx_filename,
        )
        elements = partition_docx(
            filename=docx_filename,
            metadata_filename=metadata_filename,
            include_metadata=include_metadata,
            metadata_last_modified=metadata_last_modified,
        )

    return elements


def _get_emphasized_texts_from_paragraph(paragraph: Paragraph) -> List[dict]:
    """Get emphasized texts with bold/italic formatting from a paragraph in MS Word"""
    emphasized_texts = []
    for run in paragraph.runs:
        text = run.text.strip() if run.text else None
        if not text:
            continue
        if run.bold:
            emphasized_texts.append({"text": text, "tag": "b"})
        if run.italic:
            emphasized_texts.append({"text": text, "tag": "i"})
    return emphasized_texts


def _get_emphasized_texts_from_table(table: DocxTable) -> List[dict]:
    emphasized_texts = []
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                _emphasized_texts = _get_emphasized_texts_from_paragraph(paragraph)
                emphasized_texts += _emphasized_texts
    return emphasized_texts
