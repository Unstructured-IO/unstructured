from __future__ import annotations

from typing import IO, Any, Optional

from markdown_it import MarkdownIt

from unstructured.documents.elements import Element
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import exactly_one
from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.html import partition_html
from unstructured.safe_http import safe_get
from unstructured.telemetry import partition_runtime_telemetry


def optional_decode(contents: str | bytes) -> str:
    if isinstance(contents, bytes):
        return contents.decode("utf-8")
    return contents


DETECTION_ORIGIN: str = "md"

# NOTE: the entries below are the only supported ``extensions`` values. "tables"
# toggles GFM-style table parsing; "fenced_code" is accepted for backward
# compatibility but fenced code blocks are part of CommonMark and are always
# parsed. Any other value raises ValueError (see _validate_markdown_extensions).
_DEFAULT_MARKDOWN_EXTENSIONS: list[str] = ["tables", "fenced_code"]

_SUPPORTED_MARKDOWN_EXTENSIONS: frozenset[str] = frozenset({"tables", "fenced_code"})


def _validate_markdown_extensions(extensions: Any) -> list[str]:
    """Return ``extensions`` if it is a list of supported extension names.

    The Markdown converter is CommonMark (via ``markdown-it-py``), so the only
    meaningful toggle is ``"tables"``. ``"fenced_code"`` is accepted but has no
    effect because fenced code blocks are part of CommonMark. Python-Markdown
    extension names and ``Extension`` instances are no longer supported.
    """
    if not isinstance(extensions, list):
        raise ValueError(
            "'extensions' must be a list of extension names (str), "
            f"got {type(extensions).__name__!r}"
        )
    for item in extensions:
        if not isinstance(item, str) or item not in _SUPPORTED_MARKDOWN_EXTENSIONS:
            raise ValueError(
                "Each entry in 'extensions' must be one of the supported extension "
                f"names {sorted(_SUPPORTED_MARKDOWN_EXTENSIONS)}, got {item!r}. "
                "Python-Markdown extension names and Extension instances are not supported."
            )
    return extensions


def _markdown_to_html(text: str, extensions: list[str]) -> str:
    """Convert Markdown to HTML with CommonMark plus optional table parsing.

    CommonMark (unlike the previous Python-Markdown converter) parses a list
    block that directly follows an intro line, which fixes #3280: without a
    blank line, "My list / - item 1 ..." no longer folds into a single
    paragraph instead of a list.
    """
    parser = MarkdownIt("commonmark", {"html": True})
    if "tables" in extensions:
        parser.enable("table")
    return parser.render(text)


@partition_runtime_telemetry("md")
def partition_md(
    filename: str | None = None,
    file: IO[bytes] | None = None,
    text: str | None = None,
    url: str | None = None,
    metadata_filename: str | None = None,
    metadata_last_modified: str | None = None,
    languages: Optional[list[str]] = None,
    *,
    encoding: str | None = None,
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
    encoding
        The source encoding for filename, file, or URL bytes. When None, local files use
        best-effort detection and URLs use the HTTP response's encoding. An explicit
        encoding is decoded strictly and is never replaced by an automatic guess.

    Other keyword arguments are forwarded to ``partition_html``. Markdown is converted to HTML
    with CommonMark (via ``markdown-it-py``), so a list block directly following an intro
    line parses as a list (see #3280); the previous Python-Markdown converter required a
    blank line there. ``extensions`` is a list of supported extension names (``str``). The
    default is ``["tables", "fenced_code"]``: ``"tables"`` enables GFM-style table parsing,
    and ``"fenced_code"`` is accepted but has no effect because fenced code blocks are part
    of CommonMark and are always parsed. Any other value raises ``ValueError``;
    Python-Markdown extension names and ``Extension`` instances are no longer supported.
    """
    # -- an empty document yields no elements, like the other text-based partitioners --
    if text == "" and file is None and filename is None and url is None:
        return []

    if text is None:
        text = ""

    # -- verify that only one of the arguments was provided --
    exactly_one(filename=filename, file=file, text=text, url=url)

    last_modified = get_last_modified_date(filename) if filename else None

    if filename is not None:
        _, text = read_txt_file(filename=filename, encoding=encoding)

    elif file is not None:
        _, text = read_txt_file(file=file, encoding=encoding)

    elif url is not None:
        response = safe_get(url)
        if not response.ok:
            raise ValueError(f"URL return an error: {response.status_code}")

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("text/markdown"):
            raise ValueError(
                f"Expected content type text/markdown. Got {content_type}.",
            )

        text = response.content.decode(encoding) if encoding else response.text

    # -- optional markdown extensions; default matches historical partition_md behavior --
    extensions = _validate_markdown_extensions(
        kwargs.pop("extensions", _DEFAULT_MARKDOWN_EXTENSIONS)
    )

    html = _markdown_to_html(text, extensions)

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
