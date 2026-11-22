from __future__ import annotations

import re
from typing import IO, Any, Optional

import markdown
from markdown.extensions import Extension

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

_DEFAULT_MARKDOWN_EXTENSIONS: list[str] = ["tables", "fenced_code"]

# -- a YAML front-matter block: a `---` line at the very start of the document, closed by a
# -- `---` or `...` line --
_FRONT_MATTER_RE = re.compile(
    r"\A\ufeff?---[ \t]*\r?\n(?P<body>.*?)^(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)",
    re.DOTALL | re.MULTILINE,
)
# -- `key: value` with a key as static site generators spell it: one lowercase word. Prose such as
# -- `Notice: ...` or `See also: ...` does not match.
_FRONT_MATTER_ENTRY_RE = re.compile(r"(?P<key>[a-z_][\w.-]*):(?:[ \t]+(?P<value>.*))?")
_BLOCK_SCALAR_RE = re.compile(r"[|>][+-]?(?:[ \t]+#.*)?")
_CLOSING_DELIMITER = {'"': '"', "'": "'", "[": "]", "{": "}"}


def _is_yaml_value(value: str) -> bool:
    """True when `value` is a complete single-line YAML scalar or flow collection."""
    closing_delimiter = _CLOSING_DELIMITER.get(value[0])
    if closing_delimiter is not None:
        return len(value) > 1 and value.endswith(closing_delimiter)
    # -- these characters cannot start a plain YAML scalar, and `: ` cannot appear inside one --
    return value[0] not in "*&!%@`|>,]}#" and not re.search(r":(?:\s|$)", value)


def _is_yaml_metadata(body: str) -> bool:
    """True when every line of `body` belongs to a YAML mapping as used for front matter.

    This accepts a conservative subset of YAML: `key: value` entries, lists and nested mappings
    under a key, and block scalars. Everything that is also ordinary Markdown is rejected, including
    blank lines, headings (which look like YAML comments), and lines of prose, so text that only
    resembles front matter is never discarded.
    """
    keys: set[str] = set()
    # -- what the indented lines after the current key may be: None means no such line is allowed --
    nested: Optional[str] = None

    for line in body.splitlines():
        content = line.strip()
        if not content:
            return False

        is_indented = line[0] in " \t"
        if is_indented and nested == "block scalar":
            continue
        if nested == "collection" and content.startswith("- "):
            item = content[2:].strip()
            entry = _FRONT_MATTER_ENTRY_RE.fullmatch(item)
            value = entry.group("value") if entry else item
            if value and not _is_yaml_value(value.strip()):
                return False
            continue

        entry = _FRONT_MATTER_ENTRY_RE.fullmatch(content)
        if entry is None:
            return False
        value = (entry.group("value") or "").strip()
        is_block_scalar = bool(_BLOCK_SCALAR_RE.fullmatch(value))
        if value and not is_block_scalar and not _is_yaml_value(value):
            return False
        if is_indented:
            if nested != "collection" or is_block_scalar:
                return False
            continue

        if entry.group("key") in keys:
            return False
        keys.add(entry.group("key"))
        nested = "block scalar" if is_block_scalar else None if value else "collection"

    return bool(keys)


def _strip_front_matter(text: str) -> str:
    """Return `text` without a leading YAML front-matter block, as used by static site generators.

    Python-Markdown has no notion of front matter, so the block would be rendered as a thematic
    break plus a paragraph, or as a setext heading when the block has one line. The block is removed
    only when all of it is YAML metadata, so a document that starts with a thematic break followed
    by ordinary content is not changed.
    """
    match = _FRONT_MATTER_RE.match(text)
    if match is None or not _is_yaml_metadata(match.group("body")):
        return text
    return text[match.end() :]


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
    skip_front_matter: bool = True,
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
    skip_front_matter
        When True (the default), a YAML front-matter block at the start of the document (`---` ...
        `---`), as used by Jekyll, Hugo, Docusaurus and similar tools, is not part of the content
        and is skipped. The block is kept unless all of it is YAML metadata. Use False to pass the
        document to Markdown unchanged, for example when a custom extension reads front matter.

    Other keyword arguments are forwarded to ``partition_html``. In addition, ``extensions`` may be
    passed to ``markdown.markdown()`` as a list of registered extension names (``str``) and/or
    configured ``markdown.extensions.Extension`` instances. The default is
    ``["tables", "fenced_code"]``. Pass e.g. ``extensions=["tables"]`` if you need the legacy
    behavior where ``#`` inside unfenced content is parsed as a heading (see #4006).
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

    if skip_front_matter:
        text = _strip_front_matter(text)

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
