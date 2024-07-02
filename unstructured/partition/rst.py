from __future__ import annotations

from typing import IO, Any, Optional

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.file_conversion import convert_file_to_html_text_using_pandoc
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import exactly_one, get_last_modified
from unstructured.partition.html import partition_html

DETECTION_ORIGIN: str = "rst"


@process_metadata()
@add_metadata_with_filetype(FileType.RST)
@add_chunking_strategy
def partition_rst(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    languages: Optional[list[str]] = ["auto"],
    detect_language_per_element: bool = False,
    date_from_file_object: bool = False,
    **kwargs: Any,
) -> list[Element]:
    """Partitions an RST document. The document is first converted to HTML and then
    partitioned using partition_html.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
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
    """
    exactly_one(filename=filename, file=file)

    html_text = convert_file_to_html_text_using_pandoc(
        source_format="rst", filename=filename, file=file
    )

    return partition_html(
        text=html_text,
        encoding="unicode",
        metadata_filename=metadata_filename,
        metadata_last_modified=(
            metadata_last_modified or get_last_modified(filename, file, date_from_file_object)
        ),
        languages=languages,
        detect_language_per_element=detect_language_per_element,
        detection_origin=DETECTION_ORIGIN,
    )
