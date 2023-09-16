from __future__ import annotations

import io
from tempfile import SpooledTemporaryFile
from typing import IO, Any, Iterator, List, Optional, Union

import pptx
from pptx.shapes.autoshape import Shape
from pptx.shapes.base import BaseShape
from pptx.shapes.graphfrm import GraphicFrame
from pptx.shapes.shapetree import SlideShapes
from pptx.text.text import _Paragraph  # pyright: ignore [reportPrivateUsage]

from unstructured.chunking.title import add_chunking_strategy
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    EmailAddress,
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
)
from unstructured.partition.text_type import (
    is_email_address,
    is_possible_narrative_text,
    is_possible_title,
)

OPENXML_SCHEMA_NAME = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


@process_metadata()
@add_metadata_with_filetype(FileType.PPTX)
@add_chunking_strategy()
def partition_pptx(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = True,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    metadata_last_modified: Optional[str] = None,
    include_slide_notes: bool = False,
    chunking_strategy: Optional[str] = None,
    **kwargs: Any,
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
    metadata_last_modified
        The last modified date for the document.
    include_slide_notes
        If True, includes the slide notes as element
    """
    # -- verify only one source-file argument was provided --
    exactly_one(filename=filename, file=file)

    if isinstance(file, SpooledTemporaryFile):
        file.seek(0)
        file = io.BytesIO(file.read())

    source_file = file or filename
    assert source_file is not None

    return list(
        _PptxPartitioner.iter_presentation_elements(
            source_file,
            include_page_breaks,
            include_slide_notes,
            metadata_filename,
            metadata_last_modified,
        )
    )


class _PptxPartitioner:  # pyright: ignore[reportUnusedClass]
    """Provides `.partition()` for PowerPoint 2007+ (.pptx) files."""

    def __init__(
        self,
        file: Union[str, IO[bytes]],
        # -- having default values for these arguments is not necessary for production uses because
        # -- this object is always created by the classmethod. However it simplifies constructing
        # -- this object in tests and makes them less sensitive to signature changes.
        include_page_breaks: bool = True,
        include_slide_notes: bool = False,
        metadata_filename: Optional[str] = None,
        metadata_last_modified: Optional[str] = None,
    ) -> None:
        self._file = file
        self._include_page_breaks = include_page_breaks
        self._include_slide_notes = include_slide_notes
        self._metadata_filename = metadata_filename
        self._metadata_last_modified = metadata_last_modified

    @classmethod
    def iter_presentation_elements(
        cls,
        file: Union[str, IO[bytes]],
        include_page_breaks: bool,
        include_slide_notes: bool,
        metadata_filename: Optional[str],
        metadata_last_modified: Optional[str],
    ) -> Iterator[Element]:
        """Partition MS Word documents (.docx format) into its document elements."""
        return cls(
            file,
            include_page_breaks,
            include_slide_notes,
            metadata_filename,
            metadata_last_modified,
        )._iter_presentation_elements()

    def _iter_presentation_elements(self) -> Iterator[Element]:
        """Generate each document-element in presentation in document order."""
        filename = self._file if isinstance(self._file, str) else None

        last_modification_date = None
        if filename:
            if not filename.startswith("/tmp"):
                last_modification_date = get_last_modified_date(filename)
        else:
            assert not isinstance(self._file, str)
            last_modification_date = get_last_modified_date_from_file(self._file)

        presentation = pptx.Presentation(self._file)

        metadata = ElementMetadata(filename=self._metadata_filename or filename)
        num_slides = len(presentation.slides)
        for i, slide in enumerate(presentation.slides):
            metadata = ElementMetadata.from_dict(metadata.to_dict())
            metadata.last_modified = self._metadata_last_modified or last_modification_date
            metadata.page_number = i + 1
            if self._include_slide_notes and slide.has_notes_slide is True:
                notes_slide = slide.notes_slide
                if notes_slide.notes_text_frame is not None:
                    notes_text_frame = notes_slide.notes_text_frame
                    notes_text = notes_text_frame.text
                    if notes_text.strip() != "":
                        yield NarrativeText(text=notes_text, metadata=metadata)

            for shape in _order_shapes(slide.shapes):
                if shape.has_table:
                    assert isinstance(shape, GraphicFrame)
                    table = shape.table
                    html_table = convert_ms_office_table_to_text(table, as_html=True)
                    text_table = convert_ms_office_table_to_text(table, as_html=False).strip()
                    if text_table:
                        metadata = ElementMetadata(
                            filename=self._metadata_filename or filename,
                            text_as_html=html_table,
                            page_number=metadata.page_number,
                            last_modified=self._metadata_last_modified or last_modification_date,
                        )
                        yield Table(text=text_table, metadata=metadata)
                    continue
                if not shape.has_text_frame:
                    continue
                assert isinstance(shape, Shape)
                # NOTE(robinson) - avoid processing shapes that are not on the actual slide
                # NOTE - skip check if no top or left position (shape displayed top left)
                if (shape.top and shape.left) and (shape.top < 0 or shape.left < 0):
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text
                    if text.strip() == "":
                        continue
                    if _is_bulleted_paragraph(paragraph):
                        yield ListItem(text=text, metadata=metadata)
                    elif is_email_address(text):
                        yield EmailAddress(text=text)
                    elif is_possible_narrative_text(text):
                        yield NarrativeText(text=text, metadata=metadata)
                    elif is_possible_title(text):
                        yield Title(text=text, metadata=metadata)
                    else:
                        yield Text(text=text, metadata=metadata)

            if self._include_page_breaks and i < num_slides - 1:
                yield PageBreak(text="")


def _order_shapes(shapes: SlideShapes) -> List[BaseShape]:
    """Orders the shapes from top to bottom and left to right."""
    return sorted(shapes, key=lambda x: (x.top or 0, x.left or 0))


def _is_bulleted_paragraph(paragraph: _Paragraph) -> bool:
    """True when `paragraph` has a bullet-charcter prefix.

    Bullet characters in the openxml schema are represented by buChar.
    """
    paragraph_xml = paragraph._p.get_or_add_pPr()
    buChar = paragraph_xml.find(f"{OPENXML_SCHEMA_NAME}buChar")
    return buChar is not None
