from typing import IO, TYPE_CHECKING, Dict, List, Optional

import requests

from unstructured.documents.elements import Element, process_metadata
from unstructured.documents.html import HTMLDocument
from unstructured.documents.xml import VALID_PARSERS
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.file_conversion import convert_file_to_html_text
from unstructured.file_utils.filetype import (
    FileType,
    add_metadata_with_filetype,
    document_to_element_list,
)
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)

if TYPE_CHECKING:
    from unstructured_inference.inference.layout import DocumentLayout


@process_metadata()
@add_metadata_with_filetype(FileType.HTML)
def partition_html(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    url: Optional[str] = None,
    encoding: Optional[str] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    headers: Dict[str, str] = {},
    ssl_verify: bool = True,
    parser: VALID_PARSERS = None,
    html_assemble_articles: bool = False,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    skip_headers_and_footers: bool = False,
    **kwargs,
) -> List[Element]:
    """Partitions an HTML document into its constituent elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "r" mode --> open(filename, "r").
    text
        The string representation of the HTML document.
    url
        The URL of a webpage to parse. Only for URLs that return an HTML document.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    include_page_breaks
        If True, includes page breaks at the end of each page in the document.
    include_metadata
        Optionally allows for excluding metadata from the output. Primarily intended
        for when partition_html is called in other partition bricks (like partition_email)
    headers
        The headers to be used in conjunction with the HTTP request if URL is set.
    ssl_verify
        If the URL parameter is set, determines whether or not partition uses SSL verification
        in the HTTP request.
    parser
        The parser to use for parsing the HTML document. If None, default parser will be used.
    metadata_last_modified
        The last modified date for the document.
    skip_headers_and_footers
        If True, ignores any content that is within <header> or <footer> tags

    """
    if text is not None and text.strip() == "" and not file and not filename and not url:
        return []
    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file, text=text, url=url)

    last_modification_date = None
    if filename is not None:
        last_modification_date = get_last_modified_date(filename)
        document = HTMLDocument.from_file(
            filename,
            parser=parser,
            encoding=encoding,
            assemble_articles=html_assemble_articles,
        )

    elif file is not None:
        last_modification_date = get_last_modified_date_from_file(file)
        _, file_text = read_txt_file(file=file, encoding=encoding)
        document = HTMLDocument.from_string(
            file_text,
            parser=parser,
            assemble_articles=html_assemble_articles,
        )

    elif text is not None:
        _text: str = str(text)
        document = HTMLDocument.from_string(
            _text,
            parser=parser,
            assemble_articles=html_assemble_articles,
        )

    elif url is not None:
        response = requests.get(url, headers=headers, verify=ssl_verify)
        if not response.ok:
            raise ValueError(f"URL return an error: {response.status_code}")

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("text/html"):
            raise ValueError(f"Expected content type text/html. Got {content_type}.")

        document = HTMLDocument.from_string(response.text, parser=parser)

    if skip_headers_and_footers:
        document = filter_footer_and_header(document)

    return document_to_element_list(
        document,
        include_page_breaks=include_page_breaks,
        last_modification_date=metadata_last_modified or last_modification_date,
    )


def convert_and_partition_html(
    source_format: str,
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
) -> List[Element]:
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
    last_modication_date
        The last modified date for the document.
    """

    last_modification_date = None
    if filename:
        last_modification_date = get_last_modified_date(filename)
    elif file:
        last_modification_date = get_last_modified_date_from_file(file)
    html_text = convert_file_to_html_text(
        source_format=source_format,
        filename=filename,
        file=file,
    )
    # NOTE(robinson) - pypandoc returns a text string with unicode encoding
    # ref: https://github.com/JessicaTegner/pypandoc#usage
    return partition_html(
        text=html_text,
        include_page_breaks=include_page_breaks,
        encoding="unicode",
        metadata_filename=metadata_filename,
        metadata_last_modified=metadata_last_modified or last_modification_date,
    )


def filter_footer_and_header(document: "DocumentLayout") -> "DocumentLayout":
    for page in document.pages:
        page.elements = list(
            filter(
                lambda el: "footer" not in el.ancestortags and "header" not in el.ancestortags,
                page.elements,
            ),
        )
    return document
