from __future__ import annotations

import functools
import importlib.util
import json
import os
import re
import zipfile
from typing import IO, Callable, List, Optional

from typing_extensions import ParamSpec

from unstructured.documents.elements import Element
from unstructured.file_utils.encoding import detect_file_encoding, format_encoding_str
from unstructured.file_utils.model import PLAIN_TEXT_EXTENSIONS, FileType
from unstructured.logger import logger
from unstructured.nlp.patterns import EMAIL_HEAD_RE, LIST_OF_DICTS_PATTERN
from unstructured.partition.common import (
    add_element_metadata,
    exactly_one,
    remove_element_metadata,
    set_element_hierarchy,
)
from unstructured.utils import get_call_args_applying_defaults

LIBMAGIC_AVAILABLE = bool(importlib.util.find_spec("magic"))


def detect_filetype(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    file_filename: Optional[str] = None,
    encoding: Optional[str] = "utf-8",
) -> Optional[FileType]:
    """Use libmagic to determine a file's type.

    Helps determine which partition brick to use for a given file. A return value of None indicates
    a non-supported file type.
    """
    mime_type = None
    exactly_one(filename=filename, file=file)

    # first check (content_type)
    if content_type:
        file_type = FileType.from_mime_type(content_type)
        if file_type:
            return file_type

    # second check (filename/file_name/file)
    # continue if successfully define mime_type
    if filename or file_filename:
        _filename = filename or file_filename or ""
        _, extension = os.path.splitext(_filename)
        extension = extension.lower()
        if os.path.isfile(_filename) and LIBMAGIC_AVAILABLE:
            import magic

            mime_type = magic.from_file(_resolve_symlink(_filename), mime=True)
        elif os.path.isfile(_filename):
            import filetype as ft

            mime_type = ft.guess_mime(_filename)
        if mime_type is None:
            return FileType.from_extension(extension) or FileType.UNK

    elif file is not None:
        if hasattr(file, "name"):
            _, extension = os.path.splitext(file.name)
        else:
            extension = ""
        extension = extension.lower()
        # NOTE(robinson) - the python-magic docs recommend reading at least the first 2048 bytes
        # Increased to 4096 because otherwise .xlsx files get detected as a zip file
        # ref: https://github.com/ahupp/python-magic#usage
        if LIBMAGIC_AVAILABLE:
            import magic

            mime_type = magic.from_buffer(file.read(4096), mime=True)
        else:
            import filetype as ft

            mime_type = ft.guess_mime(file.read(4096))
        if mime_type is None:
            logger.warning(
                "libmagic is unavailable but assists in filetype detection on file-like objects. "
                "Please consider installing libmagic for better results.",
            )
            return FileType.from_extension(extension) or FileType.UNK

    else:
        raise ValueError("No filename, file, nor file_filename were specified.")

    """Mime type special cases."""
    # third check (mime_type)

    # NOTE(Crag): older magic lib does not differentiate between xls and doc
    if mime_type == "application/msword" and extension == ".xls":
        return FileType.XLS

    elif mime_type.endswith("xml"):
        if extension == ".html" or extension == ".htm":
            return FileType.HTML
        else:
            return FileType.XML

    # -- ref: https://www.rfc-editor.org/rfc/rfc822 --
    elif mime_type == "message/rfc822" or mime_type.startswith("text"):
        if not encoding:
            encoding = "utf-8"
        formatted_encoding = format_encoding_str(encoding)

        if extension in [
            ".eml",
            ".p7s",
            ".md",
            ".rtf",
            ".html",
            ".rst",
            ".org",
            ".csv",
            ".tsv",
            ".json",
        ]:
            return FileType.from_extension(extension)

        # NOTE(crag): for older versions of the OS libmagic package, such as is currently
        # installed on the Unstructured docker image, .json files resolve to "text/plain"
        # rather than "application/json". this corrects for that case.
        if _is_text_file_a_json(
            file=file,
            filename=filename,
            encoding=formatted_encoding,
        ):
            return FileType.JSON

        if _is_text_file_a_csv(
            file=file,
            filename=filename,
            encoding=formatted_encoding,
        ):
            return FileType.CSV

        if file and _check_eml_from_buffer(file=file) is True:
            return FileType.EML

        if extension in PLAIN_TEXT_EXTENSIONS:
            return FileType.from_extension(extension) or FileType.UNK

        # Safety catch
        if file_type := FileType.from_mime_type(mime_type):
            return file_type

        return FileType.TXT

    elif mime_type == "application/octet-stream":
        if extension == ".docx":
            return FileType.DOCX
        elif file:
            return _detect_filetype_from_octet_stream(file=file)
        else:
            return FileType.from_extension(extension) or FileType.UNK

    elif mime_type == "application/zip":
        file_type = FileType.UNK
        if file:
            file_type = _detect_filetype_from_octet_stream(file=file)
        elif filename is not None:
            with open(filename, "rb") as f:
                file_type = _detect_filetype_from_octet_stream(file=f)

        extension = extension if extension else ""
        return (
            FileType.ZIP
            if file_type in (FileType.UNK, FileType.ZIP)
            else FileType.from_extension(extension) or file_type
        )

    elif _is_code_mime_type(mime_type):
        # NOTE(robinson) - we'll treat all code files as plain text for now.
        # we can update this logic and add filetypes for specific languages
        # later if needed.
        return FileType.TXT

    elif mime_type.endswith("empty"):
        return FileType.EMPTY

    # For everything else
    elif file_type := FileType.from_mime_type(mime_type):
        return file_type

    logger.warning(
        f"The MIME type{f' of {filename!r}' if filename else ''} is {mime_type!r}. "
        "This file type is not currently supported in unstructured.",
    )
    return FileType.from_extension(extension) or FileType.UNK


def is_json_processable(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    file_text: Optional[str] = None,
    encoding: Optional[str] = "utf-8",
) -> bool:
    """True when file looks like a JSON array of objects.

    Uses regex on a file prefix, so not entirely reliable but good enough if you already know the
    file is JSON.
    """
    exactly_one(filename=filename, file=file, file_text=file_text)
    if file_text is None:
        file_text = _read_file_start_for_type_check(
            file=file,
            filename=filename,
            encoding=encoding,
        )
    return re.match(LIST_OF_DICTS_PATTERN, file_text) is not None


def _check_eml_from_buffer(file: IO[bytes] | IO[str]) -> bool:
    """Checks if a text/plain file is actually a .eml file.

    Uses a regex pattern to see if the start of the file matches the typical pattern for a .eml
    file.
    """
    file.seek(0)
    file_content = file.read(4096)
    if isinstance(file_content, bytes):
        file_head = file_content.decode("utf-8", errors="ignore")
    else:
        file_head = file_content
    return EMAIL_HEAD_RE.match(file_head) is not None


def _detect_filetype_from_octet_stream(file: IO[bytes]) -> FileType:
    """Detects the filetype, given a file with an application/octet-stream MIME type."""
    file.seek(0)
    if zipfile.is_zipfile(file):
        file.seek(0)
        archive = zipfile.ZipFile(file)

        # NOTE(robinson) - .docx.xlsx files are actually zip file with a .docx/.xslx extension.
        # If the MIME type is application/octet-stream, we check if it's a .docx/.xlsx file by
        # looking for expected filenames within the zip file.
        archive_filenames = [f.filename for f in archive.filelist]
        if all(f in archive_filenames for f in ("docProps/core.xml", "word/document.xml")):
            return FileType.DOCX
        elif all(f in archive_filenames for f in ("xl/workbook.xml",)):
            return FileType.XLSX
        elif all(f in archive_filenames for f in ("docProps/core.xml", "ppt/presentation.xml")):
            return FileType.PPTX

    if LIBMAGIC_AVAILABLE:
        import magic

        # Infer mime type using magic if octet-stream is not zip file
        mime_type = magic.from_buffer(file.read(4096), mime=True)
        return FileType.from_mime_type(mime_type) or FileType.UNK
    logger.warning(
        "Could not detect the filetype from application/octet-stream MIME type.",
    )
    return FileType.UNK


def _is_code_mime_type(mime_type: str) -> bool:
    """True when `mime_type` plausibly indicates a programming language source-code file."""
    PROGRAMMING_LANGUAGES = [
        "javascript",
        "python",
        "java",
        "c++",
        "cpp",
        "csharp",
        "c#",
        "php",
        "ruby",
        "swift",
        "typescript",
    ]
    mime_type = mime_type.lower()
    # NOTE(robinson) - check this one explicitly to avoid conflicts with other
    # MIME types that contain "go"
    if mime_type == "text/x-go":
        return True
    return any(language in mime_type for language in PROGRAMMING_LANGUAGES)


def _is_text_file_a_csv(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    encoding: Optional[str] = "utf-8",
):
    """Detects if a file that has a text/plain MIME type is a CSV file."""

    def count_commas(text: str):
        """Counts the number of commas in a line, excluding commas in quotes."""
        pattern = r"(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$),"
        matches = re.findall(pattern, text)
        return len(matches)

    file_text = _read_file_start_for_type_check(
        file=file,
        filename=filename,
        encoding=encoding,
    )
    lines = file_text.strip().splitlines()
    if len(lines) < 2:
        return False
    lines = lines[: len(lines)] if len(lines) < 10 else lines[:10]
    header_count = count_commas(lines[0])
    if any("," not in line for line in lines):
        return False
    return all(count_commas(line) == header_count for line in lines[1:])


def _is_text_file_a_json(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    encoding: Optional[str] = "utf-8",
):
    """Detects if a file that has a text/plain MIME type is a JSON file."""
    file_text = _read_file_start_for_type_check(
        file=file,
        filename=filename,
        encoding=encoding,
    )
    try:
        output = json.loads(file_text)
        # NOTE(robinson) - Per RFC 4627 which defines the application/json media type,
        # a string is a valid JSON. For our purposes, however, we want to treat that
        # as a text file even if it is serializable as json.
        # References:
        # https://stackoverflow.com/questions/7487869/is-this-simple-string-considered-valid-json
        # https://www.ietf.org/rfc/rfc4627.txt
        return not isinstance(output, str)
    except json.JSONDecodeError:
        return False


def _read_file_start_for_type_check(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    encoding: Optional[str] = "utf-8",
) -> str:
    """Reads the start of the file and returns the text content."""
    exactly_one(filename=filename, file=file)

    if file is not None:
        file.seek(0)
        file_content = file.read(4096)
        if isinstance(file_content, str):
            file_text = file_content
        else:
            file_text = file_content.decode(errors="ignore")
        file.seek(0)
        return file_text

    # -- guaranteed by `exactly_one()` call --
    assert filename is not None

    try:
        with open(filename, encoding=encoding) as f:
            file_text = f.read(4096)
    except UnicodeDecodeError:
        formatted_encoding, _ = detect_file_encoding(filename=filename)
        with open(filename, encoding=formatted_encoding) as f:
            file_text = f.read(4096)

    return file_text


def _resolve_symlink(file_path: str) -> str:
    """Resolve `file_path` containing symlink to the actual file path."""
    if os.path.islink(file_path):
        file_path = os.path.realpath(file_path)
    return file_path


_P = ParamSpec("_P")


def add_metadata(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> List[Element]:
        elements = func(*args, **kwargs)
        call_args = get_call_args_applying_defaults(func, *args, **kwargs)
        include_metadata = call_args.get("include_metadata", True)
        if include_metadata:
            if call_args.get("metadata_filename"):
                call_args["filename"] = call_args.get("metadata_filename")

            metadata_kwargs = {
                kwarg: call_args.get(kwarg) for kwarg in ("filename", "url", "text_as_html")
            }
            # NOTE (yao): do not use cast here as cast(None) still is None
            if not str(kwargs.get("model_name", "")).startswith("chipper"):
                # NOTE(alan): Skip hierarchy if using chipper, as it should take care of that
                elements = set_element_hierarchy(elements)

            for element in elements:
                # NOTE(robinson) - Attached files have already run through this logic
                # in their own partitioning function
                if element.metadata.attached_to_filename is None:
                    add_element_metadata(element, **metadata_kwargs)

            return elements
        else:
            return remove_element_metadata(elements)

    return wrapper


def add_filetype(
    filetype: FileType,
) -> Callable[[Callable[_P, List[Element]]], Callable[_P, List[Element]]]:
    """Post-process element-metadata for list[Element] from partitioning.

    This decorator adds a post-processing step to a document partitioner.

    - Adds `metadata_filename` and `include_metadata` parameters to docstring if not present.
    - Adds `.metadata.regex-metadata` when `regex_metadata` keyword-argument is provided.
    - Updates element.id to a UUID when `unique_element_ids` argument is provided and True.

    """

    def decorator(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> List[Element]:
            elements = func(*args, **kwargs)
            params = get_call_args_applying_defaults(func, *args, **kwargs)
            include_metadata = params.get("include_metadata", True)
            if include_metadata:
                for element in elements:
                    # NOTE(robinson) - Attached files have already run through this logic
                    # in their own partitioning function
                    if element.metadata.attached_to_filename is None:
                        add_element_metadata(element, filetype=filetype.mime_type)

                return elements
            else:
                return remove_element_metadata(elements)

        return wrapper

    return decorator


def add_metadata_with_filetype(
    filetype: FileType,
) -> Callable[[Callable[_P, List[Element]]], Callable[_P, List[Element]]]:
    """..."""

    def decorator(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
        return add_filetype(filetype=filetype)(add_metadata(func))

    return decorator
