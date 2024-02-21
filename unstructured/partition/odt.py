from typing import Any, BinaryIO, List, Optional

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.docx import convert_and_partition_docx


@process_metadata()
@add_metadata_with_filetype(FileType.ODT)
@add_chunking_strategy()
def partition_odt(
    filename: Optional[str] = None,
    file: Optional[BinaryIO] = None,
    include_metadata: bool = True,
    infer_table_structure: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    languages: Optional[List[str]] = ["auto"],
    detect_language_per_element: bool = False,
    **kwargs: Any,
) -> List[Element]:
    """Partitions Open Office Documents in .odt format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
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
    """

    last_modification_date = None
    if filename:
        last_modification_date = get_last_modified_date(filename)
    elif file:
        last_modification_date = get_last_modified_date_from_file(file)

    return convert_and_partition_docx(
        source_format="odt",
        filename=filename,
        file=file,
        infer_table_structure=infer_table_structure,
        metadata_filename=metadata_filename,
        metadata_last_modified=metadata_last_modified or last_modification_date,
        languages=languages,
        detect_language_per_element=detect_language_per_element,
    )
