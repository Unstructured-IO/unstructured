from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

import xml.etree.ElementTree as ET

from unstructured.documents.elements import ElementMetadata
from unstructured.partition.common import exactly_one, spooled_to_bytes_io_if_needed
from unstructured.partition.text import partition_text
from unstructured.staging.base import elements_to_json


def is_leaf(elem):
    return not bool(elem)


def get_leaf_elements(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    xml_path: str = ".",
):
    if filename:
        tree = ET.parse(filename)
    else:
        f = (
            spooled_to_bytes_io_if_needed(
                cast(Union[BinaryIO, SpooledTemporaryFile], file)
            ),
        )
        tree = ET.parse(f)

    root = tree.getroot()
    leaf_elements = []

    for elem in root.findall(xml_path):
        for subelem in elem.iter():
            if is_leaf(subelem):
                leaf_elements.append(subelem.text)

    return "\n".join(leaf_elements)


def partition_xml(
    filename: Optional[str] = None,
    file: Optional[Union[IO, SpooledTemporaryFile]] = None,
    xml_path: str = ".",
    metadata_filename: Optional[str] = None,
):
    exactly_one(filename=filename, file=file)
    metadata_filename = metadata_filename or filename
    raw_text = get_leaf_elements(filename=filename, file=file, xml_path=xml_path)
    elements = partition_text(text=raw_text, metadata_filename=metadata_filename)
    return elements
