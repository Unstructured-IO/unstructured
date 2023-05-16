import xml.etree.ElementTree as ET
from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, Optional, Union, cast

from unstructured.partition.common import exactly_one, spooled_to_bytes_io_if_needed
from unstructured.partition.text import partition_text


def is_leaf(elem):
    return not bool(elem)


def get_leaf_elements(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    xml_path: str = ".",
):
    if filename:
        tree = ET.parse(filename)
    elif file:
        f = (
            spooled_to_bytes_io_if_needed(
                cast(Union[BinaryIO, SpooledTemporaryFile], file),
            ),
        )
        tree = ET.parse(f)  # type: ignore

    root = tree.getroot()
    leaf_elements = []

    for elem in root.findall(xml_path):
        for subelem in elem.iter():
            if is_leaf(subelem):
                leaf_elements.append(subelem.text)

    return "\n".join(leaf_elements)  # type: ignore


def partition_xml(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    keep_xml_tags: bool = False,
    xml_path: str = ".",
    metadata_filename: Optional[str] = None,
    encoding: str = "utf-8",
):
    exactly_one(filename=filename, file=file)
    metadata_filename = metadata_filename or filename

    if keep_xml_tags:
        if filename:
            with open(filename) as f:
                raw_text = f.read()
        elif file:
            raw_text = file.read().decode(encoding)
    else:
        raw_text = get_leaf_elements(filename=filename, file=file, xml_path=xml_path)
    elements = partition_text(text=raw_text, metadata_filename=metadata_filename)
    return elements
