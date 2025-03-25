# pyright: reportPrivateUsage=false

"""Provides `partition_html()."""

from __future__ import annotations

from typing import IO, Any, Iterator, List, Literal, Optional, cast

import requests
from lxml import etree

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, ElementType
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.model import FileType
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date
from unstructured.partition.html.parser import Flow, html_parser
from unstructured.partition.html.transformations import (
    ontology_to_unstructured_elements,
    parse_html_to_ontology,
)
from unstructured.utils import is_temp_file_path, lazyproperty


@apply_metadata(FileType.HTML)
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
    skip_headers_and_footers: bool = False,
    detection_origin: Optional[str] = None,
    html_parser_version: Literal["v1", "v2"] = "v1",
    image_alt_mode: Optional[Literal["to_text"]] = "to_text",
    extract_image_block_to_payload: bool = False,
    extract_image_block_types: Optional[list[str]] = None,
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
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    skip_headers_and_footers
        If True, ignores any content that is within <header> or <footer> tags

    html_parser_version (Literal['v1', 'v2']):
        The version of the HTML parser to use. The default is 'v1'. For 'v2' the parser will
        use the ontology schema to parse the HTML document.

    image_alt_mode (Literal['to_text']):
        When set 'to_text', the v2 parser will include the alternative text of images in the output.
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
        skip_headers_and_footers=skip_headers_and_footers,
        detection_origin=detection_origin,
        html_parser_version=html_parser_version,
        image_alt_mode=image_alt_mode,
        extract_image_block_types=extract_image_block_types,
        extract_image_block_to_payload=extract_image_block_to_payload,
    )

    return list(_HtmlPartitioner.iter_elements(opts))


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
        skip_headers_and_footers: bool,
        detection_origin: str | None,
        html_parser_version: Literal["v1", "v2"] = "v1",
        image_alt_mode: Optional[Literal["to_text"]] = "to_text",
        extract_image_block_types: Optional[list[str]] = None,
        extract_image_block_to_payload: bool = False,
    ):
        self._file_path = file_path
        self._file = file
        self._text = text
        self._encoding = encoding
        self._url = url
        self._headers = headers
        self._ssl_verify = ssl_verify
        self._skip_headers_and_footers = skip_headers_and_footers
        self._detection_origin = detection_origin
        self._html_parser_version = html_parser_version
        self._image_alt_mode = image_alt_mode
        self._extract_image_block_types = extract_image_block_types
        self._extract_image_block_to_payload = extract_image_block_to_payload

    @lazyproperty
    def detection_origin(self) -> str | None:
        """Trace of initial partitioner to be included in metadata for debugging purposes."""
        return self._detection_origin

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
        return (
            None
            if not self._file_path or is_temp_file_path(self._file_path)
            else get_last_modified_date(self._file_path)
        )

    @lazyproperty
    def skip_headers_and_footers(self) -> bool:
        """When True, elements located within a header or footer are pruned."""
        return self._skip_headers_and_footers

    @lazyproperty
    def html_parser_version(self) -> Literal["v1", "v2"]:
        """When html_parser_version=='v2', HTML elements follow ontology schema."""
        return self._html_parser_version

    @lazyproperty
    def add_img_alt_text(self) -> bool:
        """When True, the alternative text of images is included in the output."""
        return self._image_alt_mode == "to_text"


class _HtmlPartitioner:
    """Partition HTML document into document-elements."""

    def __init__(self, opts: HtmlPartitionerOptions):
        self._opts = opts

    def _should_include_image_base64(self, element: Element) -> bool:
        """Determines if an image_base64 element should be included in the output."""
        return (
            element.category == ElementType.IMAGE
            and self._opts._extract_image_block_to_payload
            and self._opts._extract_image_block_types is not None
            and "Image" in self._opts._extract_image_block_types
        )

    @classmethod
    def iter_elements(cls, opts: HtmlPartitionerOptions) -> Iterator[Element]:
        """Partition HTML document provided by `opts` into document-elements."""
        yield from cls(opts)._iter_elements()

    def _iter_elements(self) -> Iterator[Element]:
        """Generated document-elements (e.g. Title, NarrativeText, etc.) parsed from document.

        Elements appear in document order.
        """
        elements_iter = (
            self._main.iter_elements()
            if self._opts.html_parser_version == "v1"
            else self._from_ontology
        )

        for e in elements_iter:
            e.metadata.last_modified = self._opts.last_modified
            e.metadata.detection_origin = self._opts.detection_origin

            # -- remove <image_base64> if not requested --
            if not self._should_include_image_base64(e):
                e.metadata.image_base64 = None
                e.metadata.image_mime_type = None
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
            root, ["del", "link", "meta", "noscript", "script", "style"], with_tail=False
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

    @lazyproperty
    def _from_ontology(self) -> List[Element]:
        """Convert an ontology elements represented in HTML to an ontology element."""
        html_text = self._opts.html_text
        ontology = parse_html_to_ontology(html_text)
        unstructured_elements = ontology_to_unstructured_elements(
            ontology, add_img_alt_text=self._opts.add_img_alt_text
        )
        return unstructured_elements
