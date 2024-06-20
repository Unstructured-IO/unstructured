# pyright: reportPrivateUsage=false

"""Provides `partition_html()."""

from __future__ import annotations

from typing import IO, Any, Iterator, Optional, cast

import requests
from lxml import etree

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.documents.html import HTMLDocument
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import get_last_modified_date, get_last_modified_date_from_file
from unstructured.partition.html.parser import Flow, html_parser
from unstructured.partition.lang import apply_lang_metadata
from unstructured.utils import is_temp_file_path, lazyproperty


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


class HtmlPartitionerOptions:
    """Encapsulates partitioning option validation, computation, and application of defaults."""

    def __init__(
        self,
        *,
        file_path: str | None,
        file: IO[bytes] | None,
        text: str | None,
        encoding: str | None,
        url: str | None,
        headers: dict[str, str],
        ssl_verify: bool,
        date_from_file_object: bool,
        metadata_last_modified: str | None,
        skip_headers_and_footers: bool,
        detection_origin: str | None,
    ):
        self._file_path = file_path
        self._file = file
        self._text = text
        self._encoding = encoding
        self._url = url
        self._headers = headers
        self._ssl_verify = ssl_verify
        self._date_from_file_object = date_from_file_object
        self._metadata_last_modified = metadata_last_modified
        self._skip_headers_and_footers = skip_headers_and_footers
        self._detection_origin = detection_origin

    @lazyproperty
    def detection_origin(self) -> str | None:
        """Trace of initial partitioner to be included in metadata for debugging purposes."""
        return self._detection_origin

    @lazyproperty
    def encoding(self) -> str | None:
        """Caller-provided encoding used to store HTML character stream as bytes.

        `None` when no encoding was provided and encoding should be auto-detected.
        """
        return self._encoding

    @lazyproperty
    def html_text(self) -> str:
        """The HTML document as a string, loaded from wherever the caller specified."""
        if self._file_path:
            return read_txt_file(filename=self._file_path, encoding=self._encoding)[1]

        if self._file:
            return read_txt_file(file=self._file, encoding=self._encoding)[1]

        if self._text:
            return str(self._text)

        if self._url:
            response = requests.get(self._url, headers=self._headers, verify=self._ssl_verify)
            if not response.ok:
                raise ValueError(
                    f"Error status code on GET of provided URL: {response.status_code}"
                )
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("text/html"):
                raise ValueError(f"Expected content type text/html. Got {content_type}.")

            return response.text

        raise ValueError("Exactly one of filename, file, text, or url must be specified.")

    @lazyproperty
    def last_modified(self) -> str | None:
        """The best last-modified date available, None if no sources are available."""
        # -- Value explicitly specified by caller takes precedence. This is used for example when
        # -- this file was converted from another format.
        if self._metadata_last_modified:
            return self._metadata_last_modified

        if self._file_path:
            return (
                None
                if is_temp_file_path(self._file_path)
                else get_last_modified_date(self._file_path)
            )

        if self._file:
            return (
                get_last_modified_date_from_file(self._file)
                if self._date_from_file_object
                else None
            )

        return None

    @lazyproperty
    def skip_headers_and_footers(self) -> bool:
        """When True, elements located within a header or footer are pruned."""
        return self._skip_headers_and_footers


class _HtmlPartitioner:  # pyright: ignore[reportUnusedClass]
    """Partition HTML document into document-elements."""

    def __init__(self, opts: HtmlPartitionerOptions):
        self._opts = opts

    @classmethod
    def iter_elements(cls, opts: HtmlPartitionerOptions) -> Iterator[Element]:
        """Partition HTML document provided by `opts` into document-elements."""
        yield from cls(opts)._iter_elements()

    def _iter_elements(self) -> Iterator[Element]:
        """Generated document-elements (e.g. Title, NarrativeText, etc.) parsed from document.

        Elements appear in document order.
        """
        for e in self._main.iter_elements():
            e.metadata.last_modified = self._opts.last_modified
            e.metadata.detection_origin = self._opts.detection_origin
            yield e

    @lazyproperty
    def _main(self) -> Flow:
        """The root HTML element."""
        # NOTE(scanny) - get `html_text` first so any encoding error raised is not confused with a
        # recoverable parsing error.
        html_text = self._opts.html_text

        # NOTE(scanny) - `lxml` will not parse a `str` that includes an XML encoding declaration
        # and will raise the following error:
        #     ValueError: Unicode strings with encoding declaration are not supported. ...
        # This is not valid HTML (would be in XHTML), but Chrome accepts it so we work around it
        # by UTF-8 encoding the str bytes and parsing those.
        try:
            root = etree.fromstring(html_text, html_parser)
        except ValueError:
            root = etree.fromstring(html_text.encode("utf-8"), html_parser)

        # -- remove a variety of HTML element types like <script> and <style> that we prefer not
        # -- to encounter while parsing.
        etree.strip_elements(
            root, ["del", "img", "link", "meta", "noscript", "script", "style"], with_tail=False
        )

        # -- remove <header> and <footer> tags if the caller doesn't want their contents --
        if self._opts.skip_headers_and_footers:
            etree.strip_elements(root, ["header", "footer"], with_tail=False)

        # -- jump to the core content if the document indicates where it is --
        if (main := root.find(".//main")) is not None:
            return cast(Flow, main)
        if (body := root.find(".//body")) is not None:
            return cast(Flow, body)
        return cast(Flow, root)
