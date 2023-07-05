from typing import IO, List, Optional, Union

import markdown
import requests

from unstructured.documents.elements import Element, process_metadata
from unstructured.documents.xml import VALID_PARSERS
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import exactly_one
from unstructured.partition.html import partition_html


def optional_decode(contents: Union[str, bytes]) -> str:
    if isinstance(contents, bytes):
        return contents.decode("utf-8")
    return contents


@process_metadata()
@add_metadata_with_filetype(FileType.MD)
def partition_md(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    url: Optional[str] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    parser: VALID_PARSERS = None,
    metadata_filename: Optional[str] = None,
    **kwargs,
) -> List[Element]:
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
    """
    # Verify that only one of the arguments was provided
    if text is None:
        text = ""
    exactly_one(filename=filename, file=file, text=text, url=url)

    if filename is not None:
        with open(filename, encoding="utf8") as f:
            text = optional_decode(f.read())

    elif file is not None:
        text = optional_decode(file.read())

    elif url is not None:
        response = requests.get(url)
        if not response.ok:
            raise ValueError(f"URL return an error: {response.status_code}")

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("text/markdown"):
            raise ValueError(f"Expected content type text/markdown. Got {content_type}.")

        text = response.text

    html = markdown.markdown(text)

    return partition_html(
        text=html,
        include_page_breaks=include_page_breaks,
        include_metadata=include_metadata,
        parser=parser,
        metadata_filename=metadata_filename,
    )
