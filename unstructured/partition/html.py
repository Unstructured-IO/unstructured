from typing import IO, List, Optional

import requests

from unstructured.documents.elements import Element
from unstructured.documents.html import HTMLDocument
from unstructured.documents.xml import VALID_PARSERS
from unstructured.partition.common import add_element_metadata, document_to_element_list


def partition_html(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    url: Optional[str] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    parser: VALID_PARSERS = None,
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
    include_page_breaks
        If True, includes page breaks at the end of each page in the document.
    include_metadata
        Optionally allows for excluding metadata from the output. Primarily intended
        for when partition_html is called in other partition bricks (like partition_email)
    parser
        The parser to use for parsing the HTML document. If None, default parser will be used.
    """
    if not any([filename, file, text, url]):
        raise ValueError("One of filename, file, or text must be specified.")

    if filename is not None and not file and not text and not url:
        document = HTMLDocument.from_file(filename, parser=parser)

    elif file is not None and not filename and not text and not url:
        file_content = file.read()
        if isinstance(file_content, bytes):
            file_text = file_content.decode("utf-8")
        else:
            file_text = file_content

        document = HTMLDocument.from_string(file_text, parser=parser)

    elif text is not None and not filename and not file and not url:
        _text: str = str(text)
        document = HTMLDocument.from_string(_text, parser=parser)

    elif url is not None and not filename and not file and not text:
        response = requests.get(url)
        if not response.ok:
            raise ValueError(f"URL return an error: {response.status_code}")

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("text/html"):
            raise ValueError(f"Expected content type text/html. Got {content_type}.")

        document = HTMLDocument.from_string(response.text, parser=parser)

    else:
        raise ValueError("Only one of filename, file, or text can be specified.")

    layout_elements = document_to_element_list(document, include_page_breaks=include_page_breaks)
    if include_metadata:
        return add_element_metadata(
            layout_elements,
            include_page_breaks=include_page_breaks,
            filename=filename,
            url=url,
        )
    else:
        return layout_elements
