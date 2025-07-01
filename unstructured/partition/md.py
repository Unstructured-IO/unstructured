from __future__ import annotations

import re
from typing import IO, Any, Match

import markdown
import requests

from unstructured.documents.elements import Element
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import exactly_one
from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.html import partition_html


def optional_decode(contents: str | bytes) -> str:
    if isinstance(contents, bytes):
        return contents.decode("utf-8")
    return contents


DETECTION_ORIGIN: str = "md"


def _preprocess_markdown_code_blocks(text: str) -> str:
    """Pre-process code blocks so that processing instructions can be properly escaped.

    The markdown library can fail to properly escape processing instructions like <?xml>, <?php>,
    etc. in code blocks. This function adds minimal indentation to the processing instruction line
    to force markdown to treat it as text content rather than XML.
    """
    # Breakdown of the regex:
    # ```\s*\n           - Opening triple backticks + optional whitespace + newline
    # ([ \t]{0,3})?      - Capture group 1: optional 0-3 spaces/tabs (existing indentation)
    # (<\?[a-zA-Z][^>]*\?>.*?) - Capture group 2: processing instruction + any following content
    # \n?```             - Optional newline + closing triple backticks
    code_block_pattern = r"```\s*\n([ \t]{0,3})?(<\?[a-zA-Z][^>]*\?>.*?)\n?```"

    def indent_processing_instruction(match: Match[str]) -> str:
        content = match.group(2)
        # Ensure processing instruction has at least 4-space indentation
        if content.lstrip().startswith("<?"):
            content = "    " + content.lstrip()
        return f"```\n{content}\n```"

    return re.sub(code_block_pattern, indent_processing_instruction, text, flags=re.DOTALL)


def partition_md(
    filename: str | None = None,
    file: IO[bytes] | None = None,
    text: str | None = None,
    url: str | None = None,
    metadata_filename: str | None = None,
    metadata_last_modified: str | None = None,
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
    metadata_last_modified
        The last modified date for the document.
    """
    if text is None:
        text = ""

    # -- verify that only one of the arguments was provided --
    exactly_one(filename=filename, file=file, text=text, url=url)

    last_modified = get_last_modified_date(filename) if filename else None

    if filename is not None:
        _, text = read_txt_file(filename=filename)

    elif file is not None:
        _, text = read_txt_file(file=file)

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

    processed_text = _preprocess_markdown_code_blocks(text)
    html = markdown.markdown(processed_text, extensions=["tables"])

    return partition_html(
        text=html,
        metadata_filename=metadata_filename or filename,
        metadata_file_type=FileType.MD,
        metadata_last_modified=metadata_last_modified or last_modified,
        detection_origin=DETECTION_ORIGIN,
        **kwargs,
    )
