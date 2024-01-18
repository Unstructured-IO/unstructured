import copy
import textwrap
import os
import io
from typing import IO, Any, List, Optional

import tree_sitter

from unstructured.documents.elements import Element

from unstructured.file_utils.filetype import FileType, EXT_TO_FILETYPE, detect_filetype
from unstructured.nlp.tokenize import sent_tokenize
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.lang import apply_lang_metadata

TREE_SITTER_BUILD_PATH = "build/my-languages.so"
# TODO(Pierre) Add the other languages
FILETYPE_TO_LANG = {
    FileType.C: "c",
    FileType.GO: "go",
    FileType.PY: "python",
    FileType.CPP: "cpp",
    FileType.JS: "javascript",
    FileType.TS: "typescript",
}


def partition_code(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    encoding: Optional[str] = None,
    language: Optional[str] = None,
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    detection_origin: Optional[str] = "text",
    **kwargs: Any,
) -> List[Element]:
    """Partitions an .txt documents into its constituent paragraph elements.
    If paragraphs are below "min_partition" or above "max_partition" boundaries,
    they are combined or split.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    text
        The string representation of the .txt document.
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
        language=language,
        max_partition=max_partition,
        min_partition=min_partition,
        metadata_last_modified=metadata_last_modified,
        chunking_strategy=chunking_strategy,
        detection_origin=detection_origin,
        **kwargs,
    )


def _partition_code(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    languages: Optional[List[str]] = ["auto"],
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 50,
    metadata_last_modified: Optional[str] = None,
    detect_language_per_element: bool = False,
    detection_origin: Optional[str] = "text",
    **kwargs: Any,
) -> List[str]:
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
    language = None
    last_modification_date = None

    if filename is not None:
        try:
            with open(filename, "rb") as f:
                file_text = f.read()
            _, extension = os.path.splitext(filename)
            filetype = EXT_TO_FILETYPE.get(extension)
            if filetype:
                language = FILETYPE_TO_LANG.get(filetype)
            last_modification_date = get_last_modified_date(filename)
        except FileNotFoundError:
            raise FileNotFoundError("Provided filename is not correct")
    elif text is not None:
        file = io.BytesIO(bytes(text, "utf-8"))
    elif file is not None:
        filetype = detect_filetype(file=file)
        file_text = file.read()
        last_modification_date = get_last_modified_date_from_file(file)
        if filetype:
            language = FILETYPE_TO_LANG.get(filetype)
        else:
            raise RuntimeError("Unable to detect code file type")

    if min_partition is not None and len(file_text) < min_partition:
        raise ValueError("`min_partition` cannot be larger than the length of file contents.")

    if language is None:
        raise ValueError("No programming language provided/detected")

    try:
        LANG = tree_sitter.Language(TREE_SITTER_BUILD_PATH, name=language)
    except AttributeError:
        raise RuntimeError(f"The binary {TREE_SITTER_BUILD_PATH} does not contain {language}")

    parser = tree_sitter.Parser()
    parser.set_language(LANG)
    tree = parser.parse(file_text)
    cursor = tree.walk()
    if not tree.root_node.children or tree.root_node.children[0].type == "ERROR":
        raise ValueError(f"File is not written in {language}")

    file_content = _partition_by_node(
        node=tree.root_node,
        text=file_text.decode("utf-8"),
        min_chars=min_partition,
        max_chars=max_partition,
    )

    elements = file_content
    return elements


def _partition_by_node(
    node: tree_sitter.Node,
    text: str,
    last_end: int = 0,
    current_chunk: str = "",
    min_chars: int = 200,
    max_chars: int = 2000,
) -> list[str]:
    new_chunks = []
    for child in node.children:
        if child.end_byte - child.start_byte > max_chars:
            # Child is too big, recursively chunk the child, keep memory
            if len(current_chunk) > min_chars:
                new_chunks.append(current_chunk)
                current_chunk = ""
            new_chunks.extend(
                _partition_by_node(child, text, last_end, current_chunk)
            )
            # We might have information for the last recursive elements
            current_chunk = new_chunks[-1]
            new_chunks = new_chunks[:-1]
        elif len(current_chunk) + child.end_byte - child.start_byte > max_chars:
            # Child would make the current chunk too big, so start a new chunk
            new_chunks.append(current_chunk)
            current_chunk = text[last_end : child.end_byte]
        else:
            current_chunk += text[last_end : child.end_byte]
        last_end = child.end_byte
    if len(current_chunk) > 0:
        new_chunks.append(current_chunk)
    return new_chunks
