import tempfile
import warnings
from typing import IO, List, Optional

from ebooklib import epub

from unstructured.chunking.title import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.html import partition_html
from unstructured.partition.lang import apply_lang_metadata

DETECTION_ORIGIN: str = "epub"


@process_metadata()
@add_metadata_with_filetype(FileType.EPUB)
@add_chunking_strategy()
def partition_epub(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    encoding: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    languages: Optional[List[str]] = ["auto"],
    detect_language_per_element: bool = False,
    **kwargs,
) -> List[Element]:
    """Partitions an EPUB document. The document is first converted to HTML and then
    partitioned using partition_html. Book `section` info is included in metadata, but
    does not perfectly align with sections in document because of ebooklib constraints.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it
    metadata_last_modified
        The last modified date for the document.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    """
    exactly_one(filename=filename, file=file)

    if filename is not None:
        last_modification_date = get_last_modified_date(filename)
    elif file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.read())
            filename = tmp.name
        last_modification_date = get_last_modified_date_from_file(file)

    # NOTE(robinson): ignore ebooklib warning about changing the ignore_ncx default
    # in the future.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        book = epub.read_epub(filename, options={"ignore_ncx": False})
    # book.items also includes EpubLink, EpubImage, EpubNcx (page navigation info)
    # and EpubItem (fomatting/css)
    html_items = [item for item in book.items if isinstance(item, epub.EpubHtml)]
    toc_href_and_title = []
    elements = []

    # open issue that might resolve the chapter mapping of text
    # https://github.com/aerkalov/ebooklib/issues/289
    for item in book.toc:
        # Some toc items may be tuple of multiple items, but all have the same href
        if isinstance(item, tuple):
            toc_href_and_title.append((item[0].href.split("#")[0], item[0].title))
        else:
            toc_href_and_title.append((item.href.split("#")[0], item.title))

    item_title = None

    for item in html_items:
        if encoding:
            item_content = item.get_content().decode(encoding)
        elif filename is not None:
            item_content = item.get_content().decode()

        item_href = item.file_name

        for href, title in toc_href_and_title:
            if item_href == href:
                item_title = title

        section_elements = partition_html(
            text=item_content,
            section=item_title,
            metadata_last_modified=metadata_last_modified or last_modification_date,
            source_format="epub",
            detection_origin=DETECTION_ORIGIN,
            **kwargs,
        )

        elements.extend(section_elements)

    elements = list(
        apply_lang_metadata(
            elements,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
        ),
    )

    return elements
