import xml.etree.ElementTree as ET
from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

from unstructured.chunking.title import add_chunking_strategy
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    Text,
    process_metadata,
)
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.text import element_from_text


def is_leaf(elem):
    return not bool(elem)


def is_string(elem):
    return isinstance(elem, str) or (hasattr(elem, "text") and isinstance(elem.text, str))


def get_leaf_elements(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    text: Optional[str] = None,
    xml_path: str = ".",
    xml_keep_tags: bool = False,
) -> List[Optional[str]]:
    exactly_one(filename=filename, file=file, text=text)
    if filename:
        _, raw_text = read_txt_file(filename=filename)
    elif file:
        f = spooled_to_bytes_io_if_needed(
            cast(Union[BinaryIO, SpooledTemporaryFile], file),
        )
        _, raw_text = read_txt_file(file=f)
    elif text:
        raw_text = text

    root = ET.fromstring(raw_text)
    leaf_elements = []

    for elem in root.findall(xml_path):
        for subelem in elem.iter():
            if is_leaf(subelem) and is_string(subelem.text):
                leaf_elements.append(subelem.text)

    return leaf_elements


@process_metadata()
@add_metadata_with_filetype(FileType.XML)
@add_chunking_strategy()
def partition_xml(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    text: Optional[str] = None,
    xml_keep_tags: bool = False,
    xml_path: str = ".",
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    encoding: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    **kwargs,
) -> List[Element]:
    """Partitions an XML document into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    text
        The text of the XML file
    xml_keep_tags
        If True, will retain the XML tags in the output. Otherwise it will simply extract
        the text from within the tags.
    xml_path
        The xml_path to use for extracting the text. Only used if xml_keep_tags=False
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    include_metadata
        Determines whether or not metadata is included in the metadata attribute on the
        elements in the output.
    metadata_last_modified
        The day of the last modification
    """
    exactly_one(filename=filename, file=file, text=text)
    elements: List[Element] = []

    last_modification_date = None
    if filename:
        last_modification_date = get_last_modified_date(filename)
    elif file:
        last_modification_date = get_last_modified_date_from_file(file)

    metadata = (
        ElementMetadata(
            filename=metadata_filename or filename,
            last_modified=metadata_last_modified or last_modification_date,
        )
        if include_metadata
        else ElementMetadata()
    )

    if xml_keep_tags:
        if filename:
            _, raw_text = read_txt_file(filename=filename, encoding=encoding)
        elif file:
            f = spooled_to_bytes_io_if_needed(
                cast(Union[BinaryIO, SpooledTemporaryFile], file),
            )
            _, raw_text = read_txt_file(file=f, encoding=encoding)
        elif text:
            raw_text = text

        elements = [
            Text(text=raw_text, metadata=metadata),
        ]

    else:
        leaf_elements = get_leaf_elements(
            filename=filename,
            file=file,
            text=text,
            xml_path=xml_path,
        )
        for leaf_element in leaf_elements:
            if leaf_element:
                element = element_from_text(leaf_element)
                element.metadata = metadata
                elements.append(element)

    return elements
