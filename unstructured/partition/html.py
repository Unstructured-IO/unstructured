from typing import IO, List, Optional

from unstructured.documents.elements import Element
from unstructured.documents.html import HTMLDocument


def partition_html(
    filename: Optional[str] = None, file: Optional[IO] = None, text: Optional[str] = None
) -> List[Element]:
    """Partitions an HTML document into its constituent elements.

    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "r" mode --> open(filename, "r").
    text
        The string representation of the HTML document.
    """
    if not any([filename, file, text]):
        raise ValueError("One of filename, file, or text must be specified.")

    if filename is not None and not file and not text:
        document = HTMLDocument.from_file(filename)
        elements = document.elements

    elif file is not None and not filename and not text:
        file_content = file.read()
        if isinstance(file_content, bytes):
            file_text = file_content.decode("utf-8")
        else:
            file_text = file_content

        document = HTMLDocument.from_string(file_text)
        elements = document.elements

    elif text is not None and not filename and not file:
        _text: str = str(text)
        document = HTMLDocument.from_string(_text)
        elements = document.elements

    else:
        raise ValueError("Only one of filename, file, or text can be specified.")

    return elements
