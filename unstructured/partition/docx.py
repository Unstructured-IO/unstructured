# pyright: reportPrivateUsage=false

from __future__ import annotations

import io
import itertools
import os
import tempfile
from tempfile import SpooledTemporaryFile
from typing import (
    IO,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)

# -- CT_* stands for "complex-type", an XML element type in docx parlance --
import docx
from docx.document import Document
from docx.enum.section import WD_SECTION_START
from docx.oxml.ns import nsmap, qn
from docx.oxml.section import CT_SectPr
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.oxml.text.run import CT_R
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.section import Section, _Footer, _Header
from docx.table import Table as DocxTable
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from lxml import etree
from typing_extensions import TypeAlias

from unstructured.chunking.title import add_chunking_strategy
from unstructured.cleaners.core import clean_bullets
from unstructured.documents.elements import (
    Address,
    Element,
    ElementMetadata,
    EmailAddress,
    Footer,
    Header,
    Link,
    ListItem,
    NarrativeText,
    PageBreak,
    Table,
    Text,
    Title,
    process_metadata,
)
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    convert_ms_office_table_to_text,
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.lang import apply_lang_metadata
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_email_address,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)
from unstructured.utils import dependency_exists, lazyproperty, requires_dependencies

if dependency_exists("pypandoc"):
    import pypandoc

DETECTION_ORIGIN: str = "docx"
BlockElement: TypeAlias = Union[CT_P, CT_Tbl]
BlockItem: TypeAlias = Union[Paragraph, DocxTable]


@requires_dependencies("pypandoc")
def convert_and_partition_docx(
    source_format: str,
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    languages: Optional[List[str]] = ["auto"],
    detect_language_per_element: bool = False,
) -> List[Element]:
    """Converts a document to DOCX and then partitions it using partition_docx.

    Works with any file format support by pandoc.

    Parameters
    ----------
    source_format
        The format of the source document, .e.g. odt
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_metadata
        Determines whether or not metadata is included in the metadata attribute on the elements in
        the output.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    """
    exactly_one(filename=filename, file=file)

    def validate_filename(filename: str) -> str:
        """Return path to a file confirmed to exist on the filesystem."""
        if not os.path.exists(filename):
            raise ValueError(f"The file {filename} does not exist.")
        return filename

    def copy_to_tempfile(file: IO[bytes]) -> str:
        """Return path to temporary copy of file to be converted."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.read())
            return tmp.name

    def extract_docx_filename(file_path: str) -> str:
        """Return a filename like "foo.docx" from a path like "a/b/foo.odt" """
        # -- a/b/foo.odt -> foo.odt --
        filename = os.path.basename(file_path)
        # -- foo.odt -> foo --
        root_name, _ = os.path.splitext(filename)
        # -- foo -> foo.docx --
        return f"{root_name}.docx"

    file_path = validate_filename(filename) if filename else copy_to_tempfile(cast(IO[bytes], file))

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, extract_docx_filename(file_path))
        pypandoc.convert_file(  # pyright: ignore
            file_path,
            "docx",
            format=source_format,
            outputfile=docx_path,
        )
        elements = partition_docx(
            filename=docx_path,
            metadata_filename=metadata_filename,
            include_metadata=include_metadata,
            metadata_last_modified=metadata_last_modified,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
        )

    return elements


@process_metadata()
@add_metadata_with_filetype(FileType.DOCX)
@add_chunking_strategy()
def partition_docx(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    metadata_filename: Optional[str] = None,
    include_page_breaks: bool = True,
    include_metadata: bool = True,  # used by decorator
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,  # used by decorator
    languages: Optional[List[str]] = ["auto"],
    detect_language_per_element: bool = False,
    **kwargs: Any,  # used by decorator
) -> List[Element]:
    """Partitions Microsoft Word Documents in .docx format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_filename
        The filename to use for the metadata. Relevant because partition_doc converts the document
        to .docx before partition. We want the original source filename in the metadata.
    metadata_last_modified
        The last modified date for the document.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    """
    # -- verify that only one file-specifier argument was provided --
    exactly_one(filename=filename, file=file)

    elements = _DocxPartitioner.iter_document_elements(
        filename,
        file,
        metadata_filename,
        include_page_breaks,
        metadata_last_modified,
    )
    elements = apply_lang_metadata(
        elements=elements,
        languages=languages,
        detect_language_per_element=detect_language_per_element,
    )
    return list(elements)


class _DocxPartitioner:
    """Provides `.partition()` for MS-Word 2007+ (.docx) files."""

    # TODO: I think we can do better on metadata.filename. Should that only be populated when a
    #       `metadata_filename` argument was provided to `partition_docx()`? What about when not but
    #       we do get a `filename` arg or a `file` arg that has a `.name` attribute?
    # TODO: get last-modified date from document-properties (stored in docx package) rather than
    #       relying on last filesystem-write date; maybe fall-back to filesystem-date.
    # TODO: improve `._element_contains_pagebreak()`. It uses substring matching on the rendered
    #       XML text which is error-prone and not performant. Use XPath instead with the specific
    #       locations a page-break can be located. Also, there can be more than one, so return a
    #       count instead of a boolean.
    # TODO: Improve document-contains-pagebreaks algorithm to use XPath and to search for
    #       `w:lastRenderedPageBreak` alone. Make it independent and don't rely on anything like
    #        the "_element_contains_pagebreak()" function.
    # TODO: Improve ._is_list_item() to include list-styles such that telling whether a paragraph is
    #       a list-item is encapsulated in a single place rather than distributed around the code.
    # TODO: Improve ._is_list_item() method of detecting a numbered-list-item to use XPath instead
    #       of a substring match on the rendered XML. Include all permutations of how a numbered
    #       list can be manually applied (as opposed to by using a style).
    # TODO: Move _SectBlockIterator upstream into `python-docx`. It requires too much
    #       domain-specific knowledge to comfortable here and is of general use so welcome in the
    #       library.
    # TODO: Move Paragraph._get_paragraph_runs() monkey-patch upstream to `python-docx`.

    def __init__(
        self,
        filename: Optional[str],
        file: Optional[IO[bytes]],
        metadata_filename: Optional[str],
        include_page_breaks: bool,
        metadata_last_modified: Optional[str],
    ) -> None:
        self._filename = filename
        self._file = file
        self._metadata_filename = metadata_filename
        self._include_page_breaks = include_page_breaks
        self._metadata_last_modified = metadata_last_modified
        self._page_counter: int = 1

    @classmethod
    def iter_document_elements(
        cls,
        filename: Optional[str] = None,
        file: Optional[IO[bytes]] = None,
        metadata_filename: Optional[str] = None,
        include_page_breaks: bool = True,
        metadata_last_modified: Optional[str] = None,
    ) -> Iterator[Element]:
        """Partition MS Word documents (.docx format) into its document elements."""
        return cls(
            filename,
            file,
            metadata_filename,
            include_page_breaks,
            metadata_last_modified,
        )._iter_document_elements()

    def _iter_document_elements(self) -> Iterator[Element]:
        """Generate each document-element in (docx) `document` in document order."""
        # -- This implementation composes a collection of iterators into a "combined" iterator
        # -- return value using `yield from`. You can think of the return value as an Element
        # -- stream and each `yield from` as "add elements found by this function to the stream".
        # -- This is functionally analogous to declaring `elements: List[Element] = []` at the top
        # -- and using `elements.extend()` for the results of each of the function calls, but is
        # -- more perfomant, uses less memory (avoids producing and then garbage-collecting all
        # -- those small lists), is more flexible for later iterator operations like filter,
        # -- chain, map, etc. and is perhaps more elegant and simpler to read once you have the
        # -- concept of what it's doing. You can see the same pattern repeating in the "sub"
        # -- functions like `._iter_paragraph_elements()` where the "just return when done"
        # -- characteristic of a generator avoids repeated code to form interim results into lists.

        for section_idx, section in enumerate(self._document.sections):
            yield from self._iter_section_page_breaks(section_idx, section)
            yield from self._iter_section_headers(section)

            for block_item in _SectBlockItemIterator.iter_sect_block_items(section, self._document):
                # -- a block-item can only be a Paragraph ... --
                if isinstance(block_item, Paragraph):
                    yield from self._iter_paragraph_elements(block_item)
                    # -- a paragraph can contain a page-break --
                    yield from self._iter_maybe_paragraph_page_breaks(block_item)
                # -- ... or a Table --
                else:
                    yield from self._iter_table_element(block_item)

            yield from self._iter_section_footers(section)

    @lazyproperty
    def _document(self) -> Document:
        """The python-docx `Document` object loaded from file or filename."""
        filename, file = self._filename, self._file

        if filename is not None:
            return docx.Document(filename)

        assert file is not None
        if isinstance(file, SpooledTemporaryFile):
            file.seek(0)
            file = io.BytesIO(file.read())
        return docx.Document(file)

    @lazyproperty
    def _document_contains_pagebreaks(self) -> bool:
        """True when there is at least one page-break detected in the document."""
        return self._element_contains_pagebreak(self._document._element)

    def _element_contains_pagebreak(self, element: BaseOxmlElement) -> bool:
        """True when `element` contains a page break.

        Checks for both "hard" page breaks (page breaks explicitly inserted by the user)
        and "soft" page breaks, which are sometimes inserted by the MS Word renderer.
        Note that soft page breaks aren't always present. Whether or not pages are
        tracked may depend on your Word renderer.
        """
        page_break_indicators = [
            ["w:br", 'type="page"'],  # "Hard" page break inserted by user
            ["lastRenderedPageBreak"],  # "Soft" page break inserted by renderer
        ]
        if hasattr(element, "xml"):
            for indicators in page_break_indicators:
                if all(indicator in element.xml for indicator in indicators):
                    return True
        return False

    def _increment_page_number(self) -> Iterator[PageBreak]:
        """Increment page-number by 1 and generate a PageBreak element if enabled."""
        self._page_counter += 1
        if self._include_page_breaks:
            yield PageBreak("", detection_origin=DETECTION_ORIGIN)

    def _is_list_item(self, paragraph: Paragraph) -> bool:
        """True when `paragraph` can be identified as a list-item."""
        if is_bulleted_text(paragraph.text):
            return True

        return "<w:numPr>" in paragraph._p.xml

    def _iter_paragraph_elements(self, paragraph: Paragraph) -> Iterator[Element]:
        """Generate zero-or-one document element for `paragraph`.

        In Word, an empty paragraph is commonly used for inter-paragraph spacing. An empty paragraph
        does not contribute to the document-element stream and will not cause an element to be
        emitted.
        """
        text = paragraph.text

        # -- blank paragraphs are commonly used for spacing between paragraphs and
        # -- do not contribute to the document-element stream.
        if not text.strip():
            return

        metadata = self._paragraph_metadata(paragraph)

        # -- a list gets some special treatment --
        if self._is_list_item(paragraph):
            clean_text = clean_bullets(text).strip()
            if clean_text:
                yield ListItem(
                    text=clean_text,
                    metadata=metadata,
                    detection_origin=DETECTION_ORIGIN,
                )
            return

        # -- determine element-type from an explicit Word paragraph-style if possible --
        TextSubCls = self._style_based_element_type(paragraph)
        if TextSubCls:
            yield TextSubCls(text=text, metadata=metadata, detection_origin=DETECTION_ORIGIN)
            return

        # -- try to recognize the element type by parsing its text --
        TextSubCls = self._parse_paragraph_text_for_element_type(paragraph)
        if TextSubCls:
            yield TextSubCls(text=text, metadata=metadata, detection_origin=DETECTION_ORIGIN)
            return

        # -- if all that fails we give it the default `Text` element-type --
        yield Text(text, metadata=metadata, detection_origin=DETECTION_ORIGIN)

    def _iter_maybe_paragraph_page_breaks(self, paragraph: Paragraph) -> Iterator[PageBreak]:
        """Generate a `PageBreak` document element for each page-break in `paragraph`.

        Checks for both "hard" page breaks (page breaks explicitly inserted by the user)
        and "soft" page breaks, which are sometimes inserted by the MS Word renderer.
        Note that soft page breaks aren't always present. Whether or not pages are
        tracked may depend on your Word renderer.
        """

        def has_page_break_implementation_we_have_so_far() -> bool:
            """Needs to become more sophisticated."""
            page_break_indicators = [
                ["w:br", 'type="page"'],  # "Hard" page break inserted by user
                ["lastRenderedPageBreak"],  # "Soft" page break inserted by renderer
            ]
            for indicators in page_break_indicators:
                if all(indicator in paragraph._p.xml for indicator in indicators):
                    return True
            return False

        if not has_page_break_implementation_we_have_so_far():
            return

        yield from self._increment_page_number()

    def _iter_paragraph_emphasis(self, paragraph: Paragraph) -> Iterator[Dict[str, str]]:
        """Generate e.g. {"text": "MUST", "tag": "b"} for each emphasis in `paragraph`."""
        for run in paragraph.runs:
            text = run.text.strip() if run.text else ""
            if not text:
                continue
            if run.bold:
                yield {"text": text, "tag": "b"}
            if run.italic:
                yield {"text": text, "tag": "i"}

    def _iter_section_footers(self, section: Section) -> Iterator[Footer]:
        """Generate any `Footer` elements defined for this section.

        A Word document has up to three header and footer definition pairs for each document
        section, a primary, first-page, and even-page header and footer. The first-page pair
        applies only to the first page of the section (perhaps a title page or chapter start). The
        even-page pair is used in book-bound documents where there are both recto and verso pages
        (it is applied to verso (even-numbered) pages). A page where neither more specialized
        footer applies uses the primary footer.
        """

        def iter_footer(footer: _Footer, header_footer_type: str) -> Iterator[Footer]:
            """Generate zero-or-one Footer elements for `footer`."""
            if footer.is_linked_to_previous:
                return
            text = "\n".join([p.text for p in footer.paragraphs])
            if not text:
                return
            yield Footer(
                text=text,
                detection_origin=DETECTION_ORIGIN,
                metadata=ElementMetadata(
                    filename=self._metadata_filename,
                    header_footer_type=header_footer_type,
                    category_depth=0,
                ),
            )

        yield from iter_footer(section.footer, "primary")
        if section.different_first_page_header_footer:
            yield from iter_footer(section.first_page_footer, "first_page")
        if self._document.settings.odd_and_even_pages_header_footer:
            yield from iter_footer(section.even_page_footer, "even_page")

    def _iter_section_headers(self, section: Section) -> Iterator[Header]:
        """Generate `Header` elements for this section if it has them.

        See `._iter_section_footers()` docstring for more on docx headers and footers.
        """

        def iter_header(header: _Header, header_footer_type: str) -> Iterator[Header]:
            """Generate zero-or-one Header elements for `header`."""
            if header.is_linked_to_previous:
                return
            text = "\n".join([p.text for p in header.paragraphs])
            if not text:
                return
            yield Header(
                text=text,
                detection_origin=DETECTION_ORIGIN,
                metadata=ElementMetadata(
                    filename=self._metadata_filename,
                    header_footer_type=header_footer_type,
                    category_depth=0,  # -- headers are always at the root level}
                ),
            )

        yield from iter_header(section.header, "primary")
        if section.different_first_page_header_footer:
            yield from iter_header(section.first_page_header, "first_page")
        if self._document.settings.odd_and_even_pages_header_footer:
            yield from iter_header(section.even_page_header, "even_page")

    def _iter_section_page_breaks(self, section_idx: int, section: Section) -> Iterator[PageBreak]:
        """Generate zero-or-one `PageBreak` document elements for `section`.

        A docx section has a "start" type which can be "continuous" (no page-break), "nextPage",
        "evenPage", or "oddPage". For the next, even, and odd varieties, a `w:renderedPageBreak`
        element signals one page break. Here we only need to handle the case where we need to add
        another, for example to go from one odd page to another odd page and we need a total of
        two page-breaks.
        """

        def page_is_odd() -> bool:
            return self._page_counter % 2 == 1

        start_type = section.start_type

        # -- This method is called upon entering a new section, which happens before any paragraphs
        # -- in that section are partitioned. A rendered page-break due to a section-start occurs
        # -- in the first paragraph of the section and so occurs _later_ in the proces. Here we
        # -- predict when two page breaks will be needed and emit one of them. The second will be
        # -- emitted by the rendered page-break to follow.

        if start_type == WD_SECTION_START.EVEN_PAGE:  # noqa
            # -- on an even page we need two total, add one to supplement the rendered page break
            # -- to follow. There is no "first-document-page" special case because 1 is odd.
            if not page_is_odd():
                yield from self._increment_page_number()

        elif start_type == WD_SECTION_START.ODD_PAGE:
            # -- the first page of the document is an implicit "new" odd-page, so no page-break --
            if section_idx == 0:
                return
            if page_is_odd():
                yield from self._increment_page_number()

        # -- otherwise, start-type is one of "continuous", "new-column", or "next-page", none of
        # -- which need our help to get the page-breaks right.
        return

    def _iter_table_element(self, table: DocxTable) -> Iterator[Table]:
        """Generate zero-or-one Table element for a DOCX `w:tbl` XML element."""
        # -- at present, we always generate exactly one Table element, but we might want
        # -- to skip, for example, an empty table, or accommodate nested tables.

        html_table = convert_ms_office_table_to_text(table, as_html=True)
        text_table = convert_ms_office_table_to_text(table, as_html=False)
        emphasized_text_contents, emphasized_text_tags = self._table_emphasis(table)

        yield Table(
            text_table,
            detection_origin=DETECTION_ORIGIN,
            metadata=ElementMetadata(
                text_as_html=html_table,
                filename=self._metadata_filename,
                page_number=self._page_number,
                last_modified=self._last_modified,
                emphasized_text_contents=emphasized_text_contents or None,
                emphasized_text_tags=emphasized_text_tags or None,
            ),
        )

    def _iter_table_emphasis(self, table: DocxTable) -> Iterator[Dict[str, str]]:
        """Generate e.g. {"text": "word", "tag": "b"} for each emphasis in `table`."""
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield from self._iter_paragraph_emphasis(paragraph)

    @lazyproperty
    def _last_modified(self) -> Optional[str]:
        """Last-modified date suitable for use in element metadata."""
        # -- if this file was converted from another format, any last-modified date for the file
        # -- will be today, so we get it from the conversion step in `._metadata_last_modified`.
        if self._metadata_last_modified:
            return self._metadata_last_modified

        file_path, file = self._filename, self._file

        # -- if the file is on the filesystem, get its date from there --
        if file_path is not None:
            return None if file_path.startswith("/tmp") else get_last_modified_date(file_path)

        # -- otherwise try getting it from the file-like object (unlikely since BytesIO and its
        # -- brethren have no such metadata).
        assert file is not None
        return get_last_modified_date_from_file(file)

    @property
    def _page_number(self) -> Optional[int]:
        """The current page number, or None if we can't really tell.

        Page numbers are not added to element metadata if we can't find any page-breaks in the
        document (which may be a common case).

        In the DOCX format, determining page numbers is strictly a best-efforts attempt since actual
        page-breaks are determined at rendering time (e.g. printing) based on the fontmetrics of the
        target device. Explicit (hard) page-breaks are always recorded in the docx file but the
        rendered page-breaks are only added optionally.
        """
        return self._page_counter if self._document_contains_pagebreaks else None

    def _paragraph_emphasis(self, paragraph: Paragraph) -> Tuple[List[str], List[str]]:
        """[contents, tags] pair describing emphasized text in `paragraph`."""
        iter_p_emph, iter_p_emph_2 = itertools.tee(self._iter_paragraph_emphasis(paragraph))
        return ([e["text"] for e in iter_p_emph], [e["tag"] for e in iter_p_emph_2])

    def _paragraph_link_meta(self, paragraph: Paragraph) -> Tuple[List[str], List[str], List[Link]]:
        """Describes hyperlinks in `paragraph`, if any."""
        if not paragraph.hyperlinks:
            return [], [], []

        def iter_paragraph_links() -> Iterator[Link]:
            """Generate `Link` typed-dict for each external link in `paragraph`.

            Word uses hyperlinks for internal "jumps" within the document, as well as for web and
            other external locations. Only generate the external ones.
            """
            offset = 0
            for item in paragraph.iter_inner_content():
                if isinstance(item, Run):
                    offset += len(item.text)
                elif isinstance(item, Hyperlink):  # pyright: ignore[reportUnnecessaryIsInstance]
                    text = item.text
                    url = item.url
                    start_index = offset
                    offset += len(text)
                    # -- docx hyperlinks include "internal" links, like a table-of-contents
                    # -- (TOC) entry has a jump to the named heading in the document (e.g.
                    # -- '#_Toc147925734'. Such links have a fragment but not an address
                    # -- (URL). Treat those as regular text.
                    if not url:
                        continue
                    # -- all Word hyperlinks should contain text, otherwise they have no
                    # -- visual appearance on the document. Not expected, but technically possible
                    # -- so filter these out too.
                    if not text:
                        continue
                    yield Link(text=text, url=url, start_index=start_index)

        links = list(iter_paragraph_links())
        # -- link["text"] is allowed to be None by the declared type for `Link`, but never will be
        # -- here because such a link is filtered out above. Use empty str to satisfy type-checker.
        link_texts = [link["text"] or "" for link in links]
        link_urls = [link["url"] for link in links]
        return link_texts, link_urls, links

    def _paragraph_metadata(self, paragraph: Paragraph) -> ElementMetadata:
        """ElementMetadata object describing `paragraph`."""
        category_depth = self._parse_category_depth_by_style(paragraph)
        emphasized_text_contents, emphasized_text_tags = self._paragraph_emphasis(paragraph)
        link_texts, link_urls, links = self._paragraph_link_meta(paragraph)
        element_metadata = ElementMetadata(
            category_depth=category_depth,
            emphasized_text_contents=emphasized_text_contents or None,
            emphasized_text_tags=emphasized_text_tags or None,
            filename=self._metadata_filename,
            last_modified=self._last_modified,
            link_texts=link_texts or None,
            link_urls=link_urls or None,
            links=links or None,
            page_number=self._page_number,
        )
        element_metadata.detection_origin = "docx"
        return element_metadata

    def _parse_paragraph_text_for_element_type(self, paragraph: Paragraph) -> Optional[Type[Text]]:
        """Attempt to differentiate the element-type by inspecting the raw text."""
        text = paragraph.text.strip()

        if len(text) < 2:
            return None
        if is_us_city_state_zip(text):
            return Address
        if is_email_address(text):
            return EmailAddress
        if is_possible_narrative_text(text):
            return NarrativeText
        if is_possible_title(text):
            return Title

        return None

    def _style_based_element_type(self, paragraph: Paragraph) -> Optional[Type[Text]]:
        """Element-type for `paragraph` based on its paragraph-style.

        Returns `None` when the style doesn't tell us anything useful, including when it
        is the default "Normal" style.
        """
        # NOTE(robinson) - documentation on built-in styles at the link below:
        # https://python-docx.readthedocs.io/en/latest/user/styles-understanding.html \
        # #paragraph-styles-in-default-template
        STYLE_TO_ELEMENT_MAPPING = {
            "Caption": Text,  # TODO(robinson) - add caption element type
            "Heading 1": Title,
            "Heading 2": Title,
            "Heading 3": Title,
            "Heading 4": Title,
            "Heading 5": Title,
            "Heading 6": Title,
            "Heading 7": Title,
            "Heading 8": Title,
            "Heading 9": Title,
            "Intense Quote": Text,  # TODO(robinson) - add quote element type
            "List": ListItem,
            "List 2": ListItem,
            "List 3": ListItem,
            "List Bullet": ListItem,
            "List Bullet 2": ListItem,
            "List Bullet 3": ListItem,
            "List Continue": ListItem,
            "List Continue 2": ListItem,
            "List Continue 3": ListItem,
            "List Number": ListItem,
            "List Number 2": ListItem,
            "List Number 3": ListItem,
            "List Paragraph": ListItem,
            "Macro Text": Text,
            "No Spacing": Text,
            "Quote": Text,  # TODO(robinson) - add quote element type
            "Subtitle": Title,
            "TOCHeading": Title,
            "Title": Title,
        }

        # -- paragraph.style can be None in rare cases, so can style.name. That's going
        # -- to mean default style which is equivalent to "Normal" for our purposes.
        style_name = (paragraph.style and paragraph.style.name) or "Normal"

        # NOTE(robinson) - The "Normal" style name will return None since it's not
        # in the mapping. Unknown style names will also return None.
        return STYLE_TO_ELEMENT_MAPPING.get(style_name)

    def _table_emphasis(self, table: DocxTable) -> Tuple[List[str], List[str]]:
        """[contents, tags] pair describing emphasized text in `table`."""
        iter_tbl_emph, iter_tbl_emph_2 = itertools.tee(self._iter_table_emphasis(table))
        return ([e["text"] for e in iter_tbl_emph], [e["tag"] for e in iter_tbl_emph_2])

    def _parse_category_depth_by_style(self, paragraph: Paragraph) -> int:
        """Determine category depth from paragraph metadata"""

        # Determine category depth from paragraph ilvl xpath
        xpath = paragraph._element.xpath("./w:pPr/w:numPr/w:ilvl/@w:val")
        if xpath:
            return int(xpath[0])

        # Determine category depth from style name
        style_name = (paragraph.style and paragraph.style.name) or "Normal"
        depth = self._parse_category_depth_by_style_name(style_name)

        if depth > 0:
            return depth
        else:
            # Check if category depth can be determined from style ilvl
            return self._parse_category_depth_by_style_ilvl()

    def _parse_category_depth_by_style_name(self, style_name: str) -> int:
        """Parse category-depth from the style-name of `paragraph`.

        Category depth is 0-indexed and relative to the other element types in the document.
        """

        def _extract_number(suffix: str) -> int:
            return int(suffix.split()[-1]) - 1 if suffix.split()[-1].isdigit() else 0

        # Heading styles
        if style_name.startswith("Heading"):
            return _extract_number(style_name)

        if style_name == "Subtitle":
            return 1

        # List styles
        list_prefixes = ["List", "List Bullet", "List Continue", "List Number"]
        if any(style_name.startswith(prefix) for prefix in list_prefixes):
            return _extract_number(style_name)

        # Other styles
        return 0

    def _parse_category_depth_by_style_ilvl(self) -> int:
        # TODO(newelh) Parsing category depth by style ilvl is not yet implemented
        return 0


class _SectBlockItemIterator:
    """Generates the block-items in a section.

    A block item is a docx Paragraph or Table. This small class is separated from
    `_SectBlockElementIterator` because these two aspects will live in different places upstream.
    This makes them easier to transplant, which we expect to do soon.
    """

    @classmethod
    def iter_sect_block_items(cls, section: Section, document: Document) -> Iterator[BlockItem]:
        """Generate each Paragraph or Table object in `section`."""
        for element in _SectBlockElementIterator.iter_sect_block_elements(section._sectPr):
            yield (
                Paragraph(element, document)
                if isinstance(element, CT_P)
                else DocxTable(element, document)
            )


class _SectBlockElementIterator:
    """Generates the block-item XML elements in a section.

    A block-item element is a `CT_P` (paragraph) or a `CT_Tbl` (table).
    """

    _compiled_blocks_xpath: Optional[etree.XPath] = None
    _compiled_count_xpath: Optional[etree.XPath] = None

    def __init__(self, sectPr: CT_SectPr):
        self._sectPr = sectPr

    @classmethod
    def iter_sect_block_elements(cls, sectPr: CT_SectPr) -> Iterator[BlockElement]:
        """Generate each CT_P or CT_Tbl element within the extents governed by `sectPr`."""
        return cls(sectPr)._iter_sect_block_elements()

    def _iter_sect_block_elements(self) -> Iterator[BlockElement]:
        """Generate each CT_P or CT_Tbl element in section."""
        # -- General strategy is to get all block (<w;p> and <w:tbl>) elements from start of doc
        # -- to and including this section, then compute the count of those elements that came
        # -- from prior sections and skip that many to leave only the ones in this section. It's
        # -- possible to express this "between here and there" (end of prior section and end of
        # -- this one) concept in XPath, but it would be harder to follow because there are
        # -- special cases (e.g. no prior section) and the boundary expressions are fairly hairy.
        # -- I also believe it would be computationally more expensive than doing it this
        # -- straighforward albeit (theoretically) slightly wasteful way.

        sectPr, sectPrs = self._sectPr, self._sectPrs
        sectPr_idx = sectPrs.index(sectPr)

        # -- count block items belonging to prior sections --
        n_blks_to_skip = (
            0
            if sectPr_idx == 0
            else self._count_of_blocks_in_and_above_section(sectPrs[sectPr_idx - 1])
        )

        # -- and skip those in set of all blks from doc start to end of this section --
        for element in self._blocks_in_and_above_section(sectPr)[n_blks_to_skip:]:
            yield element

    def _blocks_in_and_above_section(self, sectPr: CT_SectPr) -> Sequence[BlockElement]:
        """All ps and tbls in section defined by `sectPr` and all prior sections."""
        if self._compiled_blocks_xpath is None:
            self._compiled_blocks_xpath = etree.XPath(
                self._blocks_in_and_above_section_xpath,
                namespaces=nsmap,
                regexp=False,
            )
        xpath = self._compiled_blocks_xpath
        # -- XPath callable results are Any (basically), so need a cast --
        return cast(Sequence[BlockElement], xpath(sectPr))

    @lazyproperty
    def _blocks_in_and_above_section_xpath(self) -> str:
        """XPath expr for ps and tbls in context of a sectPr and all prior sectPrs."""
        # -- "p_sect" is a section with sectPr located at w:p/w:pPr/w:sectPr. "body_sect" is a
        # -- section with sectPr located at w:body/w:sectPr. The last section in the document is a
        # -- "body_sect". All others are of the "p_sect" variety. "term" means "terminal", like
        # -- the last p or tbl in the section. "pred" means "predecessor", like a preceding p or
        # -- tbl in the section.

        # -- the terminal block in a p-based sect is the p the sectPr appears in --
        p_sect_term_block = "./parent::w:pPr/parent::w:p"
        # -- the terminus of a body-based sect is the sectPr itself (not a block) --
        body_sect_term = "self::w:sectPr[parent::w:body]"
        # -- all the ps and tbls preceding (but not including) the context node --
        pred_ps_and_tbls = "preceding-sibling::*[self::w:p | self::w:tbl]"

        # -- p_sect_term_block and body_sect_term(inus) are mutually exclusive. So the result is
        # -- either the union of nodes found by the first two selectors or the nodes found by the
        # -- last selector, never both.
        return (
            # -- include the p containing a sectPr --
            f"{p_sect_term_block}"
            # -- along with all the blocks that precede it --
            f" | {p_sect_term_block}/{pred_ps_and_tbls}"
            # -- or all the preceding blocks if sectPr is body-based (last sectPr) --
            f" | {body_sect_term}/{pred_ps_and_tbls}"
        )

    def _count_of_blocks_in_and_above_section(self, sectPr: CT_SectPr) -> int:
        """All ps and tbls in section defined by `sectPr` and all prior sections."""
        if self._compiled_count_xpath is None:
            self._compiled_count_xpath = etree.XPath(
                f"count({self._blocks_in_and_above_section_xpath})",
                namespaces=nsmap,
                regexp=False,
            )
        xpath = self._compiled_count_xpath
        # -- numeric XPath results are always float, so need an int() conversion --
        return int(cast(float, xpath(sectPr)))

    @lazyproperty
    def _sectPrs(self) -> Sequence[CT_SectPr]:
        """All w:sectPr elements in document, in document-order."""
        return self._sectPr.xpath(
            "/w:document/w:body/w:p/w:pPr/w:sectPr | /w:document/w:body/w:sectPr",
        )


# == monkey-patch docx.text.Paragraph.runs ===========================================


def _get_paragraph_runs(paragraph: Paragraph) -> Sequence[Run]:
    """Gets all runs in paragraph, including hyperlinks python-docx skips.

    Without this, the default runs function skips over hyperlinks.

    Args:
        paragraph (Paragraph): A Paragraph object.

    Returns:
        list: A list of Run objects.
    """

    def _get_runs(node: BaseOxmlElement, parent: Paragraph) -> Iterator[Run]:
        """Recursively get runs."""
        for child in node:
            # -- the Paragraph has runs as direct children --
            if child.tag == qn("w:r"):
                yield Run(cast(CT_R, child), parent)
                continue
            # -- but it also has hyperlink children that themselves contain runs, so
            # -- recurse into those
            if child.tag == qn("w:hyperlink"):
                yield from _get_runs(child, parent)

    return list(_get_runs(paragraph._element, paragraph))


Paragraph.runs = property(  # pyright: ignore[reportGeneralTypeIssues]
    lambda self: _get_paragraph_runs(self),
)

# ====================================================================================
