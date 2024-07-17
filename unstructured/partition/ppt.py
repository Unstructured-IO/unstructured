from __future__ import annotations

import os
import tempfile
from typing import IO, Any, Optional

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import add_metadata_with_filetype
from unstructured.file_utils.model import FileType
from unstructured.partition.common import (
    convert_office_doc,
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.pptx import partition_pptx
from unstructured.partition.utils.constants import PartitionStrategy


@process_metadata()
@add_metadata_with_filetype(FileType.PPT)
@add_chunking_strategy
def partition_ppt(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    include_slide_notes: Optional[bool] = None,
    infer_table_structure: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    languages: Optional[list[str]] = ["auto"],
    detect_language_per_element: bool = False,
    date_from_file_object: bool = False,
    starting_page_number: int = 1,
    strategy: str = PartitionStrategy.FAST,
    **kwargs: Any,
) -> list[Element]:
    """Partitions Microsoft PowerPoint Documents in .ppt format into their document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_page_breaks
        If True, includes a PageBreak element between slides
    include_slide_notes
        If True, includes the slide notes as element
    infer_table_structure
        If True, any Table elements that are extracted will also have a metadata field
        named "text_as_html" where the table's text content is rendered into an html string.
        I.e., rows and cells are preserved.
        Whether True or False, the "text" field is always present in any Table element
        and is the text content of the table (no structure).
    metadata_last_modified
        The last modified date for the document.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True, attempt
        infer last_modified metadata from bytes, otherwise set it to None.
    starting_page_number
        Indicates what page number should be assigned to the first slide in the presentation.
        This information will be reflected in elements' metadata and can be be especially
        useful when partitioning a document that is part of a larger document.
    """
    # Verify that only one of the arguments was provided
    if filename is None:
        filename = ""
    exactly_one(filename=filename, file=file)

    last_modification_date = None
    if len(filename) > 0:
        _, filename_no_path = os.path.split(os.path.abspath(filename))
        base_filename, _ = os.path.splitext(filename_no_path)
        if not os.path.exists(filename):
            raise ValueError(f"The file {filename} does not exist.")
        last_modification_date = get_last_modified_date(filename)

    elif file is not None:
        last_modification_date = (
            get_last_modified_date_from_file(file) if date_from_file_object else None
        )
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        filename = tmp.name
        _, filename_no_path = os.path.split(os.path.abspath(tmp.name))

    base_filename, _ = os.path.splitext(filename_no_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        convert_office_doc(
            filename,
            tmpdir,
            target_format="pptx",
            target_filter="Impress MS PowerPoint 2007 XML",
        )
        pptx_filename = os.path.join(tmpdir, f"{base_filename}.pptx")
        elements = partition_pptx(
            filename=pptx_filename,
            detect_language_per_element=detect_language_per_element,
            include_page_breaks=include_page_breaks,
            include_slide_notes=include_slide_notes,
            infer_table_structure=infer_table_structure,
            languages=languages,
            metadata_filename=metadata_filename,
            metadata_last_modified=metadata_last_modified or last_modification_date,
            starting_page_number=starting_page_number,
            strategy=strategy,
        )

    # remove tmp.name from filename if parsing file
    if file:
        for element in elements:
            element.metadata.filename = metadata_filename

    return elements
