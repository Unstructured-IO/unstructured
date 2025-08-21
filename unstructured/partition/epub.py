from __future__ import annotations

from typing import IO, Any, Optional

from unstructured.documents.elements import Element
from unstructured.file_utils.file_conversion import convert_file_to_html_text_using_pandoc
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import exactly_one
from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.html import partition_html

DETECTION_ORIGIN: str = "epub"


def partition_epub(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    languages: Optional[list[str]] = ["auto"],
    detect_language_per_element: bool = False,
    **kwargs: Any,
) -> list[Element]:
    """Partitions an EPUB document. The document is first converted to HTML and then
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
    """
    exactly_one(filename=filename, file=file)

    last_modified = get_last_modified_date(filename) if filename else None

    html_text = convert_file_to_html_text_using_pandoc(
        source_format="epub",
        filename=filename,
        file=file,
    )

    return partition_html(
        text=html_text,
        metadata_filename=metadata_filename or filename,
        metadata_file_type=FileType.EPUB,
        metadata_last_modified=metadata_last_modified or last_modified,
        languages=languages,
        detect_language_per_element=detect_language_per_element,
        detection_origin=DETECTION_ORIGIN,
        **kwargs,
    )
