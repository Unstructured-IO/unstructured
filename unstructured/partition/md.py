from typing import IO, List, Optional, Union

import markdown
import requests

from unstructured.documents.elements import Element
from unstructured.documents.xml import VALID_PARSERS
from unstructured.partition.common import exactly_one
from unstructured.partition.html import partition_html


def optional_decode(contents: Union[str, bytes]) -> str:
    if isinstance(contents, bytes):
        return contents.decode("utf-8")
    return contents


def partition_md(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    url: Optional[str] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    parser: VALID_PARSERS = None,
) -> List[Element]:
    # Verify that only one of the arguments was provided
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

    elif text is None:
        raise ValueError("Exactly one of filename, file, url or text must be specified.")

    html = markdown.markdown(text)

    return partition_html(
        text=html,
        include_page_breaks=include_page_breaks,
        include_metadata=include_metadata,
        parser=parser,
    )
