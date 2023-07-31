import tempfile
from typing import IO, List, Optional

from ebooklib import epub

from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import exactly_one
from unstructured.partition.html import partition_html


@process_metadata()
@add_metadata_with_filetype(FileType.EPUB)
def partition_epub(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_date: Optional[str] = None,
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
    metadata_date
        The last modified date for the document.

    """
    exactly_one(filename=filename, file=file)
    if filename is None:
        filename = ""

    if file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.read())
            filename = tmp.name

    book = epub.read_epub(filename)
    toc_items = list(book.toc)
    elements = []

    for toc_item in toc_items:
        # Some toc items may be tuple
        if isinstance(toc_item, tuple):
            toc_item = toc_item[0]

        href = toc_item.href.split("#")[0]
        title = toc_item.title
        item = book.get_item_with_href(href)

        if item is not None:
            try:
                # Convert the item content to a string
                html_content = item.get_content().decode()
                section_elements = partition_html(text=html_content, epub_section=title)
            except Exception as e:
                print(f"Error reading content from item: {e}")
                section_elements = []

        elements.extend(section_elements)

    return elements
