from typing import IO, List, Optional

from unstructured.chunking.title import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.html import convert_and_partition_html

DETECTION_ORIGIN: str = "rtf"


@process_metadata()
@add_metadata_with_filetype(FileType.RTF)
@add_chunking_strategy()
def partition_rtf(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
infer_table_structure: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    languages: Optional[List[str]] = ["auto"],
    detect_language_per_element: bool = False,
    **kwargs,
) -> List[Element]:
    """Partitions an RTF document. The document is first converted to HTML and then
    partitioned using partition_html.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it
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

    return convert_and_partition_html(
        source_format="rtf",
        filename=filename,
        file=file,
        include_page_breaks=include_page_breaks,
        metadata_filename=metadata_filename,
        metadata_last_modified=metadata_last_modified,
        languages=languages,
        detect_language_per_element=detect_language_per_element,
        detection_origin=DETECTION_ORIGIN,
    )
