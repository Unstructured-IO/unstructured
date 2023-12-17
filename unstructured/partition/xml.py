import copy
from io import BytesIO
from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, Iterator, List, Optional, Union, cast

from lxml import etree

from unstructured.chunking import add_chunking_strategy
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
from unstructured.partition.lang import apply_lang_metadata
from unstructured.partition.text import element_from_text

DETECTION_ORIGIN: str = "xml"


def get_leaf_elements(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    text: Optional[str] = None,
    xml_path: Optional[str] = None,
) -> Iterator[Optional[str]]:
    """Get leaf elements from the XML tree defined in filename, file, or text."""
    exactly_one(filename=filename, file=file, text=text)
    if filename:
        return _get_leaf_elements(filename, xml_path=xml_path)
    elif file:
        f = cast(
            IO[bytes],
            spooled_to_bytes_io_if_needed(
                cast(Union[BinaryIO, SpooledTemporaryFile], file),
            ),
        )
        return _get_leaf_elements(f, xml_path=xml_path)
    else:
        b = BytesIO(bytes(cast(str, text), encoding="utf-8"))
        return _get_leaf_elements(b, xml_path=xml_path)


def _get_leaf_elements(
    file: Union[str, IO[bytes]],
    xml_path: Optional[str] = None,
) -> Iterator[Optional[str]]:
    """Parse the XML tree in a memory efficient manner if possible."""
    element_stack = []

    element_iterator = etree.iterparse(file, events=("start", "end"))
    # NOTE(alan) If xml_path is used for filtering, I've yet to find a good way to stream
    # elements through in a memory efficient way, so we bite the bullet and load it all into
    # memory.
    if xml_path is not None:
        _, element = next(element_iterator)
        compiled_path = etree.XPath(xml_path)
        element_iterator = (("end", el) for el in compiled_path(element))

    for event, element in element_iterator:
        if event == "start":
            element_stack.append(element)

        if event == "end":
            if element.text is not None and element.text.strip():
                yield element.text

            element.clear()

        while element_stack and element_stack[-1].getparent() is None:
            element_stack.pop()


@process_metadata()
@add_metadata_with_filetype(FileType.XML)
@add_chunking_strategy()
def partition_xml(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    text: Optional[str] = None,
    xml_keep_tags: bool = False,
    xml_path: Optional[str] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    encoding: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    languages: Optional[List[str]] = ["auto"],
    detect_language_per_element: bool = False,
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
        The text of the XML file.
    xml_keep_tags
        If True, will retain the XML tags in the output. Otherwise it will simply extract
        the text from within the tags.
    xml_path
        The xml_path to use for extracting the text. Only used if xml_keep_tags=False.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    include_metadata
        Determines whether or not metadata is included in the metadata attribute on the
        elements in the output.
    metadata_last_modified
        The day of the last modification.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    """
    exactly_one(filename=filename, file=file, text=text)

    elements: List[Element] = []

    last_modification_date = None
    if filename:
        last_modification_date = get_last_modified_date(filename)
    elif file:
        last_modification_date = get_last_modified_date_from_file(file)

    if include_metadata:
        metadata = ElementMetadata(
            filename=metadata_filename or filename,
            last_modified=metadata_last_modified or last_modification_date,
        )
        metadata.detection_origin = DETECTION_ORIGIN
    else:
        metadata = ElementMetadata()

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
                element.metadata = copy.deepcopy(metadata)
                elements.append(element)

    elements = list(
        apply_lang_metadata(
            elements=elements,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
        ),
    )
    return elements
