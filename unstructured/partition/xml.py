import xml.etree.ElementTree as ET
from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import exactly_one, spooled_to_bytes_io_if_needed
from unstructured.partition.text import partition_text


def is_leaf(elem):
    return not bool(elem)


def is_string(elem):
    return isinstance(elem, str) or (hasattr(elem, "text") and isinstance(elem.text, str))


def get_leaf_elements(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    xml_path: str = ".",
):
    if filename:
        _, raw_text = read_txt_file(filename=filename)
    elif file:
        f = spooled_to_bytes_io_if_needed(
            cast(Union[BinaryIO, SpooledTemporaryFile], file),
        )
        _, raw_text = read_txt_file(file=f)
    else:
        raise ValueError("Either 'filename' or 'file' must be provided.")

    root = ET.fromstring(raw_text)
    leaf_elements = []

    for elem in root.findall(xml_path):
        for subelem in elem.iter():
            if is_leaf(subelem) and is_string(subelem.text):
                leaf_elements.append(subelem.text)

    return "\n".join(leaf_elements)  # type: ignore


@process_metadata()
@add_metadata_with_filetype(FileType.XML)
def partition_xml(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    xml_keep_tags: bool = False,
    xml_path: str = ".",
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    encoding: Optional[str] = None,
    max_partition: Optional[int] = 1500,
    **kwargs,
) -> List[Element]:
    """Partitions an XML document into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    xml_keep_tags
        If True, will retain the XML tags in the output. Otherwise it will simply extract
        the text from within the tags.
    xml_path
        The xml_path to use for extracting the text. Only used if xml_keep_tags=False
    metadata_filename
        The filename to use for the metadata.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    include_metadata
        Determines whether or not metadata is included in the metadata attribute on the
        elements in the output.
    max_partition
        The maximum number of characters to include in a partition. If None is passed,
        no maximum is applied.
    """
    exactly_one(filename=filename, file=file)
    metadata_filename = metadata_filename or filename

    if xml_keep_tags:
        if filename:
            _, raw_text = read_txt_file(filename=filename, encoding=encoding)
        elif file:
            f = spooled_to_bytes_io_if_needed(
                cast(Union[BinaryIO, SpooledTemporaryFile], file),
            )
            _, raw_text = read_txt_file(file=f, encoding=encoding)
        else:
            raise ValueError("Either 'filename' or 'file' must be provided.")
    else:
        raw_text = get_leaf_elements(filename=filename, file=file, xml_path=xml_path)
    elements = partition_text(
        text=raw_text,
        metadata_filename=metadata_filename,
        include_metadata=include_metadata,
        max_partition=max_partition,
    )

    return elements
