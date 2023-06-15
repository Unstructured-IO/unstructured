from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

import pptx

from unstructured.documents.elements import (
    Element,
    ElementMetadata,
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
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.text_type import (
    is_possible_narrative_text,
    is_possible_title,
)

OPENXML_SCHEMA_NAME = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


@process_metadata()
@add_metadata_with_filetype(FileType.PPTX)
def partition_pptx(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    include_page_breaks: bool = True,
    metadata_filename: Optional[str] = None,
    **kwargs,
) -> List[Element]:
    """Partitions Microsoft PowerPoint Documents in .pptx format into its document elements.

    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_page_breaks
        If True, includes a PageBreak element between slides
    metadata_filename
        The filename to use for the metadata. Relevant because partition_ppt converts the
        document .pptx before partition. We want the original source filename in the
        metadata.
    """

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file)

    if filename is not None:
        presentation = pptx.Presentation(filename)
    elif file is not None:
        presentation = pptx.Presentation(
            spooled_to_bytes_io_if_needed(cast(Union[BinaryIO, SpooledTemporaryFile], file)),
        )

    elements: List[Element] = []
    metadata_filename = metadata_filename or filename
    metadata = ElementMetadata(filename=metadata_filename)
    num_slides = len(presentation.slides)
    for i, slide in enumerate(presentation.slides):
        metadata = ElementMetadata(**metadata.to_dict())
        metadata.page_number = i + 1

        for shape in _order_shapes(slide.shapes):
            if shape.has_table:
                table: pptx.table.Table = shape.table
                html_table = convert_ms_office_table_to_text(table, as_html=True)
                text_table = convert_ms_office_table_to_text(table, as_html=False)
                if (text_table := text_table.strip()) != "":
                    metadata = ElementMetadata(
                        filename=metadata_filename,
                        text_as_html=html_table,
                        page_number=metadata.page_number,
                    )
                    elements.append(Table(text=text_table, metadata=metadata))
                continue
            if not shape.has_text_frame:
                continue
            # NOTE(robinson) - avoid processing shapes that are not on the actual slide
            # NOTE - skip check if no top or left position (shape displayed top left)
            if (shape.top and shape.left) and (shape.top < 0 or shape.left < 0):
                continue
            for paragraph in shape.text_frame.paragraphs:
                text = paragraph.text
                if text.strip() == "":
                    continue
                if _is_bulleted_paragraph(paragraph):
                    elements.append(ListItem(text=text, metadata=metadata))
                elif is_possible_narrative_text(text):
                    elements.append(NarrativeText(text=text, metadata=metadata))
                elif is_possible_title(text):
                    elements.append(Title(text=text, metadata=metadata))
                else:
                    elements.append(Text(text=text, metadata=metadata))

        if include_page_breaks and i < num_slides - 1:
            elements.append(PageBreak())

    return elements


def _order_shapes(shapes):
    """Orders the shapes from top to bottom and left to right."""
    return sorted(shapes, key=lambda x: (x.top or 0, x.left or 0))


def _is_bulleted_paragraph(paragraph) -> bool:
    """Determines if the paragraph is bulleted by looking for a bullet character prefix. Bullet
    characters in the openxml schema are represented by buChar"""
    paragraph_xml = paragraph._p.get_or_add_pPr()
    buChar = paragraph_xml.find(f"{OPENXML_SCHEMA_NAME}buChar")
    return buChar is not None
