from __future__ import annotations

from typing import IO, Any, Optional

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.documents.html import HTMLDocument, HtmlPartitionerOptions
from unstructured.file_utils.file_conversion import convert_file_to_html_text
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import get_last_modified_date, get_last_modified_date_from_file
from unstructured.partition.lang import apply_lang_metadata


@process_metadata()
@add_metadata_with_filetype(FileType.HTML)
@add_chunking_strategy
def partition_html(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    encoding: Optional[str] = None,
    url: Optional[str] = None,
    headers: dict[str, str] = {},
    ssl_verify: bool = True,
    date_from_file_object: bool = False,
    detect_language_per_element: bool = False,
    languages: Optional[list[str]] = ["auto"],
    metadata_last_modified: Optional[str] = None,
    skip_headers_and_footers: bool = False,
    detection_origin: Optional[str] = None,
    **kwargs: Any,
) -> list[Element]:
    """Partitions an HTML document into its constituent elements.

    HTML source parameters
    ----------------------
    The HTML to be partitioned can be specified four different ways:

    filename
        A string defining the target filename path.
    file
        A file-like object using "r" mode --> open(filename, "r").
    text
        The string representation of the HTML document.
    url
        The URL of a webpage to parse. Only for URLs that return an HTML document.
    headers
        The HTTP headers to be used in the HTTP request when `url` is specified.
    ssl_verify
        If the URL parameter is set, determines whether or not SSL verification is performed
        on the HTTP request.

    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True, attempt
        infer last_modified metadata from bytes, otherwise set it to None.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.

    Other parameters
    ----------------
    include_metadata
        Optionally allows for excluding metadata from the output. Primarily intended
        for when partition_html is called by other partitioners (like partition_email).
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    metadata_last_modified
        The last modified date for the document.
    skip_headers_and_footers
        If True, ignores any content that is within <header> or <footer> tags
    source_format
        The source of the original html. If None we will return HTMLElements but for example
         partition_rst will pass a value of 'rst' so that we return Title vs HTMLTitle
    """
    # -- parser rejects an empty str, nip that edge-case in the bud here --
    if text is not None and text.strip() == "" and not file and not filename and not url:
        return []

    opts = HtmlPartitionerOptions(
        file_path=filename,
        file=file,
        text=text,
        encoding=encoding,
        url=url,
        headers=headers,
        ssl_verify=ssl_verify,
        date_from_file_object=date_from_file_object,
        metadata_last_modified=metadata_last_modified,
        skip_headers_and_footers=skip_headers_and_footers,
        detection_origin=detection_origin,
    )

    document = HTMLDocument.load(opts)

    elements = list(
        apply_lang_metadata(
            document.elements,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
        )
    )

    return elements


def convert_and_partition_html(
    source_format: str,
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    languages: Optional[list[str]] = ["auto"],
    detect_language_per_element: bool = False,
    detection_origin: Optional[str] = None,
    date_from_file_object: bool = False,
) -> list[Element]:
    """Converts a document to HTML and then partitions it using partition_html. Works with
    any file format support by pandoc.

    Parameters
    ----------
    source_format
        The format of the source document, i.e. rst
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it.
    metadata_filename
        The filename to use in element metadata.
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

    last_modification_date = None
    if filename:
        last_modification_date = get_last_modified_date(filename)
    elif file:
        last_modification_date = (
            get_last_modified_date_from_file(file) if date_from_file_object else None
        )
    html_text = convert_file_to_html_text(
        source_format=source_format,
        filename=filename,
        file=file,
    )
    # NOTE(robinson) - pypandoc returns a text string with unicode encoding
    # ref: https://github.com/JessicaTegner/pypandoc#usage
    return partition_html(
        text=html_text,
        source_format=source_format,
        include_page_breaks=include_page_breaks,
        encoding="unicode",
        metadata_filename=metadata_filename,
        metadata_last_modified=metadata_last_modified or last_modification_date,
        languages=languages,
        detect_language_per_element=detect_language_per_element,
        detection_origin=detection_origin,
    )
