from __future__ import annotations

from typing import IO, Any, Optional, Union

import markdown
import requests

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import add_metadata_with_filetype
from unstructured.file_utils.model import FileType
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.html import partition_html


def optional_decode(contents: Union[str, bytes]) -> str:
    if isinstance(contents, bytes):
        return contents.decode("utf-8")
    return contents


DETECTION_ORIGIN: str = "md"


@process_metadata()
@add_metadata_with_filetype(FileType.MD)
@add_chunking_strategy
def partition_md(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    url: Optional[str] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    languages: Optional[list[str]] = ["auto"],
    detect_language_per_element: bool = False,
    date_from_file_object: bool = False,
    **kwargs: Any,
) -> list[Element]:
    """Partitions a markdown file into its constituent elements

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    text
        The string representation of the markdown document.
    url
        The URL of a webpage to parse. Only for URLs that return a markdown document.
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it.
    include_metadata
        Determines whether or not metadata is included in the output.
    parser
        The parser to use for parsing the markdown document. If None, default parser will be used.
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
    # Verify that only one of the arguments was provided
    if text is None:
        text = ""

    exactly_one(filename=filename, file=file, text=text, url=url)

    last_modification_date = None
    if filename is not None:
        last_modification_date = get_last_modified_date(filename)
        with open(filename, encoding="utf8") as f:
            text = optional_decode(f.read())

    elif file is not None:
        last_modification_date = (
            get_last_modified_date_from_file(file) if date_from_file_object else None
        )
        text = optional_decode(file.read())

    elif url is not None:
        response = requests.get(url)
        if not response.ok:
            raise ValueError(f"URL return an error: {response.status_code}")

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("text/markdown"):
            raise ValueError(
                f"Expected content type text/markdown. Got {content_type}.",
            )

        text = response.text

    html = markdown.markdown(text, extensions=["tables"])

    return partition_html(
        text=html,
        include_page_breaks=include_page_breaks,
        include_metadata=include_metadata,
        source_format="md",
        metadata_filename=metadata_filename,
        metadata_last_modified=metadata_last_modified or last_modification_date,
        languages=languages,
        detect_language_per_element=detect_language_per_element,
        detection_origin=DETECTION_ORIGIN,
    )
