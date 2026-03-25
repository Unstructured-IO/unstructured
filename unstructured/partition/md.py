from __future__ import annotations

from typing import IO, Any, Optional

import markdown
import requests
from markdown.extensions import Extension

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

_DEFAULT_MARKDOWN_EXTENSIONS: list[str] = ["tables", "fenced_code"]


def _validate_markdown_extensions(extensions: Any) -> list[Any]:
    """Return ``extensions`` if it is a list of strings and/or ``Extension`` instances.

    Python-Markdown accepts extension entry points as registered names (``str``) or configured
    ``Extension`` instances; both are supported here. Any other shape raises ``ValueError``.
    """
    if not isinstance(extensions, list):
        raise ValueError(
            "'extensions' must be a list of extension names (str) and/or "
            f"markdown.extensions.Extension instances, got {type(extensions).__name__!r}"
        )
    for item in extensions:
        if not isinstance(item, (str, Extension)):
            raise ValueError(
                "Each entry in 'extensions' must be a str or markdown.extensions.Extension "
                f"instance, got {type(item).__name__}: {item!r}"
            )
    return extensions


def partition_md(
    filename: str | None = None,
    file: IO[bytes] | None = None,
    text: str | None = None,
    url: str | None = None,
    metadata_filename: str | None = None,
    metadata_last_modified: str | None = None,
    languages: Optional[list[str]] = None,
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
    languages
        The languages present in the document. Use ``["auto"]`` to detect (default when None).
        Use ``[""]`` to disable language detection.

    Other keyword arguments are forwarded to ``partition_html``. In addition, ``extensions`` may be
    passed to ``markdown.markdown()`` as a list of registered extension names (``str``) and/or
    configured ``markdown.extensions.Extension`` instances. The default is
    ``["tables", "fenced_code"]``. Pass e.g. ``extensions=["tables"]`` if you need the legacy
    behavior where ``#`` inside unfenced content is parsed as a heading (see #4006).
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

    # -- optional markdown extensions; default matches historical partition_md behavior --
    extensions = _validate_markdown_extensions(
        kwargs.pop("extensions", _DEFAULT_MARKDOWN_EXTENSIONS)
    )

    html = markdown.markdown(text, extensions=extensions)

    html_kwargs: dict[str, Any] = {
        "text": html,
        "metadata_filename": metadata_filename or filename,
        "metadata_file_type": FileType.MD,
        "metadata_last_modified": metadata_last_modified or last_modified,
        "detection_origin": DETECTION_ORIGIN,
        **kwargs,
    }
    if languages is not None:
        html_kwargs["languages"] = languages
    return partition_html(**html_kwargs)
