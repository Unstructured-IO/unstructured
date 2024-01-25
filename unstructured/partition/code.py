import copy
import os
import io
from typing import IO, Any, List, Optional

import tree_sitter

from unstructured.documents.elements import Code, Element, ElementMetadata, process_metadata

from unstructured.file_utils.filetype import FileType, EXT_TO_FILETYPE, detect_filetype
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)

from unstructured.utils import update_tree_sitter, get_homedir


TREE_SITTER_BUILD_PATH = os.path.join(
    get_homedir(), ".unstructured_treesitter/treesitter_build/languages.so"
)

# TODO(Pierre) Add the other languages
FILETYPE_TO_LANG = {
    FileType.C: "c",
    FileType.GO: "go",
    FileType.PY: "python",
    FileType.CPP: "cpp",
    FileType.JS: "javascript",
    FileType.TS: "typescript",
    FileType.CSHARP: "c-sharp",
    FileType.PHP: "php",
    FileType.RB: "ruby",
    FileType.SWIFT: "swift",
}

# update_tree_sitter(FILETYPE_TO_LANG.values())


def partition_code(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    encoding: Optional[str] = None,
    languages: Optional[List[str]] = None,
    programming_language: Optional[str] = None,
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 200,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    detection_origin: Optional[str] = "text",
    **kwargs: Any,
) -> List[Element]:
    """Partitions a code file into chunks that are greater than min_partition and
    smaller than max_partition.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    text
        The string representation of the code file.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    max_partition
        The maximum number of characters to include in a partition. If None is passed,
        no maximum is applied.
    min_partition
        The minimum number of characters to include in a partition.
    metadata_last_modified
        The day of the last modification
    """
    return _partition_code(
        filename=filename,
        file=file,
        text=text,
        encoding=encoding,
        languages=languages,
        programming_language=programming_language,
        max_partition=max_partition,
        min_partition=min_partition,
        metadata_last_modified=metadata_last_modified,
        chunking_strategy=chunking_strategy,
        detection_origin=detection_origin,
        **kwargs,
    )


@process_metadata()
def _partition_code(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    languages: Optional[List[str]] = None,
    programming_language: Optional[str] = None,
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 200,
    metadata_last_modified: Optional[str] = None,
    detect_language_per_element: bool = False,
    detection_origin: Optional[str] = "codefile",
    **kwargs: Any,
) -> List[Element]:
    """internal API for `partition_code`"""
    if text is not None and text.strip() == "" and not file and not filename:
        return []

    if (
        min_partition is not None
        and max_partition is not None
        and (min_partition > max_partition or min_partition < 0 or max_partition < 0)
    ):
        raise ValueError("Invalid values for min_partition and/or max_partition.")

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file, text=text)
    file_text = bytes()

    programming_language = programming_language
    last_modification_date = None

    if filename is not None:
        try:
            with open(filename, "rb") as f:
                file_text = f.read()
            _, extension = os.path.splitext(filename)
            filetype = EXT_TO_FILETYPE.get(extension)
            if filetype and programming_language is None:
                programming_language = FILETYPE_TO_LANG.get(filetype)
            last_modification_date = get_last_modified_date(filename)
        except FileNotFoundError:
            raise FileNotFoundError("Provided filename is not correct")
    elif text is not None:
        file = io.BytesIO(bytes(text, "utf-8"))

    if file is not None:
        filetype = FileType.UNK
        if programming_language is None:
            try:
                filetype = detect_filetype(file=file, file_filename=metadata_filename)
            except AttributeError:
                raise RuntimeError("Unable to detect code file type")
            finally:
                if filetype not in FILETYPE_TO_LANG.keys():
                    raise RuntimeError("Unable to detect code file type")
                else:
                    programming_language = FILETYPE_TO_LANG.get(filetype)
        file.seek(0)
        file_text = file.read()
        last_modification_date = get_last_modified_date_from_file(file)

    if min_partition is not None and len(file_text) < min_partition:
        min_partition = len(file_text)
        # raise ValueError("`min_partition` cannot be larger than the length of file contents.")

    if programming_language is None:
        raise ValueError("No programming language provided/detected")

    global TREE_SITTER_BUILD_PATH
    try:
        LANG = tree_sitter.Language(TREE_SITTER_BUILD_PATH, name=programming_language)
    except (AttributeError, OSError):
        raise ValueError(f"{programming_language} is not supported yet")

    parser = tree_sitter.Parser()
    parser.set_language(LANG)
    tree = parser.parse(file_text)
    if not tree.root_node.children or tree.root_node.children[0].type == "ERROR":
        raise ValueError(f"File is not written in {programming_language}")

    file_content, _ = _partition_by_node(
        node=tree.root_node,
        text=file_text.decode("utf-8"),
        min_chars=min_partition,
        max_chars=max_partition,
    )

    elements: List[Element] = []

    if include_metadata:
        metadata = ElementMetadata(
            filename=metadata_filename or filename,
            last_modified=metadata_last_modified or last_modification_date,
            languages=[programming_language],
        )
        metadata.detection_origin = detection_origin
    else:
        metadata = ElementMetadata()

    # Note (Pierre) Some languages (i.e Python) use blank space and tabs for semantic
    # Maybe removing the spaces is not a good idea
    for ctext in file_content:
        # Don't think it makes sens to use a coordinate system in code, TBD
        element = Code(text=ctext, coordinates=None, coordinate_system=None)
        element.metadata = copy.deepcopy(metadata)
        elements.append(element)

    return elements


def _partition_by_node(
    node: tree_sitter.Node,
    text: str,
    last_end: Optional[int] = 0,
    current_chunk: Optional[str] = "",
    min_chars: Optional[int] = 200,
    max_chars: Optional[int] = 1500,
) -> list[str]:
    new_chunks = []
    for child in node.children:
        if (child.end_byte - child.start_byte) > max_chars:
            # Child is too big, recursively chunk the child, keep memory
            if len(current_chunk) > min_chars:
                new_chunks.append(current_chunk)
                current_chunk = ""
            chunks, last_end = _partition_by_node(
                child, text, last_end, current_chunk, min_chars, max_chars
            )
            new_chunks.extend(chunks[:-1])
            current_chunk = chunks[-1] if len(chunks) > 0 else ""
        elif (len(current_chunk) + child.end_byte - child.start_byte) > max_chars and len(
            current_chunk
        ) > min_chars:
            # Child would make the current chunk too big, so start a new chunk
            new_chunks.append(current_chunk)
            current_chunk = text[last_end : child.end_byte]
        else:
            current_chunk += text[last_end : child.end_byte]
        last_end = child.end_byte
    if len(current_chunk) > 0:
        new_chunks.append(current_chunk)
    return new_chunks, last_end
