from typing import IO, List, Optional
from ebooklib import epub
import tempfile

from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.html import partition_html
from unstructured.partition.common import (
    exactly_one,
    _add_element_metadata,
)


def split_and_add_metadata_for_epub_file(filename):
    book = epub.read_epub(filename)
    toc_items = [item for item in book.toc]
    elements = []
    
    for toc_item in toc_items:
        # Some spine items may be tuple with second item as a linear flag
        if isinstance(toc_item, tuple):
            toc_item = toc_item[0]
            
        href = toc_item.href.split("#")[0]
        title = toc_item.title
        item = book.get_item_with_href(href)

        if item is not None:
            # Convert the item content to a string
            html_content = item.get_content().decode()
        
        section_elements = partition_html(text=html_content)
        
        for element in section_elements:
            _add_element_metadata(
                element, 
                epub_section=title,
            )
            elements.append(element)
    
    return elements
        
            

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
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        filename = tmp.name
        
    return split_and_add_metadata_for_epub_file(filename)
         