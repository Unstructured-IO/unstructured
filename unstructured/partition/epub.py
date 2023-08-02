import tempfile
from typing import IO, List, Optional

from ebooklib import epub

from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.html import partition_html


@process_metadata()
@add_metadata_with_filetype(FileType.EPUB)
def partition_epub(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    **kwargs,
) -> List[Element]:
    """Partitions an EPUB document. The document is first converted to HTML and then
    partitoned using partiton_html.

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
    """
    exactly_one(filename=filename, file=file)
    if filename is None:
        filename = ""

    if file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.read())
            filename = tmp.name
        last_modification_date = get_last_modified_date_from_file(file)
    else:
        last_modification_date = get_last_modified_date(filename)

    book = epub.read_epub(filename)
    html_items = [item for item in book.items if isinstance(item, epub.EpubHtml)]
    toc_href_and_title = []
    elements = []

    for item in book.toc:
        # Some toc items may be tuple of multiple items, but all have the same href
        if isinstance(item, tuple):
            toc_href_and_title.append((item[0].href.split("#")[0], item[0].title))
        else:
            toc_href_and_title.append((item.href.split("#")[0], item.title))

    for item in html_items:
        # not all html_items show up in the toc,
        # so some elements will still have `None` for metadata.section
        item_title = None
        item_content = item.get_content().decode()
        item_href = item.file_name

        for href, title in toc_href_and_title:
            if item_href == href:
                item_title = title

        section_elements = partition_html(
            text=item_content,
            section=item_title,
            metadata_last_modified=metadata_last_modified or last_modification_date,
            **kwargs,
        )

        elements.extend(section_elements)

    return elements
