from __future__ import annotations

import enum
import functools
import inspect
import json
import os
import re
import zipfile
from typing import IO, Any, Callable, Dict, List, Optional

from typing_extensions import ParamSpec

from unstructured.documents.elements import Element
from unstructured.file_utils.encoding import detect_file_encoding, format_encoding_str
from unstructured.nlp.patterns import LIST_OF_DICTS_PATTERN
from unstructured.partition.common import (
    _add_element_metadata,
    _remove_element_metadata,
    exactly_one,
    set_element_hierarchy,
)

try:
    import magic

    LIBMAGIC_AVAILABLE = True
except ImportError:  # pragma: nocover
    LIBMAGIC_AVAILABLE = False  # pragma: nocover

from unstructured.logger import logger
from unstructured.nlp.patterns import EMAIL_HEAD_RE

TXT_MIME_TYPES = [
    "text/plain",
    "message/rfc822",  # ref: https://www.rfc-editor.org/rfc/rfc822
]

# NOTE(robinson) - .docx.xlsx files are actually zip file with a .docx/.xslx extension.
# If the MIME type is application/octet-stream, we check if it's a .docx/.xlsx file by
# looking for expected filenames within the zip file.
EXPECTED_DOCX_FILES = [
    "docProps/core.xml",
    "word/document.xml",
]

EXPECTED_XLSX_FILES = [
    "xl/workbook.xml",
]

EXPECTED_PPTX_FILES = [
    "docProps/core.xml",
    "ppt/presentation.xml",
]


class FileType(enum.Enum):
    UNK = 0
    EMPTY = 1

    # MS Office Types
    DOC = 10
    DOCX = 11
    XLS = 12
    XLSX = 13
    PPT = 14
    PPTX = 15
    MSG = 16

    # Adobe Types
    PDF = 20

    # Image Types
    JPG = 30
    PNG = 31
    TIFF = 32

    # Plain Text Types
    EML = 40
    RTF = 41
    TXT = 42
    JSON = 43
    CSV = 44
    TSV = 45

    # Markup Types
    HTML = 50
    XML = 51
    MD = 52
    EPUB = 53
    RST = 54
    ORG = 55

    # Compressed Types
    ZIP = 60

    # Open Office Types
    ODT = 70

    # NOTE(robinson) - This is to support sorting for pandas groupby functions
    def __lt__(self, other):
        return self.name < other.name


STR_TO_FILETYPE = {
    "application/pdf": FileType.PDF,
    "application/msword": FileType.DOC,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
    "image/jpeg": FileType.JPG,
    "image/png": FileType.PNG,
    "image/tiff": FileType.TIFF,
    "text/plain": FileType.TXT,
    "text/x-csv": FileType.CSV,
    "application/csv": FileType.CSV,
    "application/x-csv": FileType.CSV,
    "text/comma-separated-values": FileType.CSV,
    "text/x-comma-separated-values": FileType.CSV,
    "text/csv": FileType.CSV,
    "text/tsv": FileType.TSV,
    "text/markdown": FileType.MD,
    "text/x-markdown": FileType.MD,
    "text/org": FileType.ORG,
    "text/x-rst": FileType.RST,
    "application/epub": FileType.EPUB,
    "application/epub+zip": FileType.EPUB,
    "application/json": FileType.JSON,
    "application/rtf": FileType.RTF,
    "text/rtf": FileType.RTF,
    "text/html": FileType.HTML,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
    "application/vnd.ms-excel": FileType.XLS,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PPTX,
    "application/vnd.ms-powerpoint": FileType.PPT,
    "application/xml": FileType.XML,
    "application/vnd.oasis.opendocument.text": FileType.ODT,
    "message/rfc822": FileType.EML,
    "application/x-ole-storage": FileType.MSG,
    "application/vnd.ms-outlook": FileType.MSG,
    "inode/x-empty": FileType.EMPTY,
}

MIMETYPES_TO_EXCLUDE = [
    "text/x-markdown",
    "application/epub+zip",
    "text/x-csv",
    "application/csv",
    "application/x-csv",
    "text/comma-separated-values",
    "text/x-comma-separated-values",
]

FILETYPE_TO_MIMETYPE = {v: k for k, v in STR_TO_FILETYPE.items() if k not in MIMETYPES_TO_EXCLUDE}

EXT_TO_FILETYPE = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".jpg": FileType.JPG,
    ".jpeg": FileType.JPG,
    ".txt": FileType.TXT,
    ".text": FileType.TXT,
    ".log": FileType.TXT,
    ".eml": FileType.EML,
    ".xml": FileType.XML,
    ".htm": FileType.HTML,
    ".html": FileType.HTML,
    ".md": FileType.MD,
    ".org": FileType.ORG,
    ".rst": FileType.RST,
    ".xlsx": FileType.XLSX,
    ".pptx": FileType.PPTX,
    ".png": FileType.PNG,
    ".doc": FileType.DOC,
    ".zip": FileType.ZIP,
    ".xls": FileType.XLS,
    ".ppt": FileType.PPT,
    ".rtf": FileType.RTF,
    ".json": FileType.JSON,
    ".epub": FileType.EPUB,
    ".msg": FileType.MSG,
    ".odt": FileType.ODT,
    ".csv": FileType.CSV,
    ".tsv": FileType.TSV,
    ".tab": FileType.TSV,
    ".tiff": FileType.TIFF,
    # NOTE(robinson) - for now we are treating code files as plain text
    ".js": FileType.TXT,
    ".py": FileType.TXT,
    ".java": FileType.TXT,
    ".cpp": FileType.TXT,
    ".cc": FileType.TXT,
    ".cxx": FileType.TXT,
    ".c": FileType.TXT,
    ".cs": FileType.TXT,
    ".php": FileType.TXT,
    ".rb": FileType.TXT,
    ".swift": FileType.TXT,
    ".ts": FileType.TXT,
    ".go": FileType.TXT,
    None: FileType.UNK,
}

PLAIN_TEXT_EXTENSIONS = [
    ".txt",
    ".text",
    ".eml",
    ".md",
    ".rtf",
    ".html",
    ".rst",
    ".org",
    ".csv",
    ".tsv",
    ".tab",
    ".json",
]


def _resolve_symlink(file_path):
    # Resolve the symlink to get the actual file path
    if os.path.islink(file_path):
        file_path = os.path.realpath(file_path)
    return file_path


def detect_filetype(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    file_filename: Optional[str] = None,
    encoding: Optional[str] = "utf-8",
) -> Optional[FileType]:
    """Use libmagic to determine a file's type. Helps determine which partition brick
    to use for a given file. A return value of None indicates a non-supported file type.
    """
    mime_type = None
    exactly_one(filename=filename, file=file)

    # first check (content_type)
    if content_type:
        filetype = STR_TO_FILETYPE.get(content_type)
        if filetype:
            return filetype

    # second check (filename/file_name/file)
    # continue if successfully define mime_type
    if filename or file_filename:
        _filename = filename or file_filename or ""
        _, extension = os.path.splitext(_filename)
        extension = extension.lower()
        if os.path.isfile(_filename) and LIBMAGIC_AVAILABLE:
            mime_type = magic.from_file(
                _resolve_symlink(filename or file_filename),
                mime=True,
            )  # type: ignore
        elif os.path.isfile(_filename):
            import filetype as ft

            mime_type = ft.guess_mime(filename)
        if mime_type is None:
            return EXT_TO_FILETYPE.get(extension, FileType.UNK)

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
            mime_type = magic.from_buffer(file.read(4096), mime=True)
        else:
            import filetype as ft

            mime_type = ft.guess_mime(file.read(4096))
        if mime_type is None:
            logger.warning(
                "libmagic is unavailable but assists in filetype detection on file-like objects. "
                "Please consider installing libmagic for better results.",
            )
            return EXT_TO_FILETYPE.get(extension, FileType.UNK)

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

    elif mime_type in TXT_MIME_TYPES or mime_type.startswith("text"):
        if not encoding:
            encoding = "utf-8"
        formatted_encoding = format_encoding_str(encoding)

        if extension in [
            ".eml",
            ".md",
            ".rtf",
            ".html",
            ".rst",
            ".org",
            ".csv",
            ".tsv",
            ".json",
        ]:
            return EXT_TO_FILETYPE.get(extension)

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
            return EXT_TO_FILETYPE.get(extension)

        # Safety catch
        if mime_type in STR_TO_FILETYPE:
            return STR_TO_FILETYPE[mime_type]

        return FileType.TXT

    elif mime_type == "application/octet-stream":
        if extension == ".docx":
            return FileType.DOCX
        elif file:
            return _detect_filetype_from_octet_stream(file=file)
        else:
            return EXT_TO_FILETYPE.get(extension, FileType.UNK)

    elif mime_type == "application/zip":
        filetype = FileType.UNK
        if file:
            filetype = _detect_filetype_from_octet_stream(file=file)
        elif filename is not None:
            with open(filename, "rb") as f:
                filetype = _detect_filetype_from_octet_stream(file=f)

        extension = extension if extension else ""
        if filetype == FileType.UNK:
            return FileType.ZIP
        else:
            return EXT_TO_FILETYPE.get(extension, filetype)

    elif _is_code_mime_type(mime_type):
        # NOTE(robinson) - we'll treat all code files as plain text for now.
        # we can update this logic and add filetypes for specific languages
        # later if needed.
        return FileType.TXT

    elif mime_type.endswith("empty"):
        return FileType.EMPTY

    # For everything else
    elif mime_type in STR_TO_FILETYPE:
        return STR_TO_FILETYPE[mime_type]

    logger.warning(
        f"The MIME type{f' of {filename!r}' if filename else ''} is {mime_type!r}. "
        "This file type is not currently supported in unstructured.",
    )
    return EXT_TO_FILETYPE.get(extension, FileType.UNK)


def _detect_filetype_from_octet_stream(file: IO[bytes]) -> FileType:
    """Detects the filetype, given a file with an application/octet-stream MIME type."""
    file.seek(0)
    if zipfile.is_zipfile(file):
        file.seek(0)
        archive = zipfile.ZipFile(file)

        archive_filenames = [f.filename for f in archive.filelist]
        if all(f in archive_filenames for f in EXPECTED_DOCX_FILES):
            return FileType.DOCX
        elif all(f in archive_filenames for f in EXPECTED_XLSX_FILES):
            return FileType.XLSX
        elif all(f in archive_filenames for f in EXPECTED_PPTX_FILES):
            return FileType.PPTX

    if LIBMAGIC_AVAILABLE:
        # Infer mime type using magic if octet-stream is not zip file
        mime_type = magic.from_buffer(file.read(4096), mime=True)
        return STR_TO_FILETYPE.get(mime_type, FileType.UNK)
    logger.warning(
        "Could not detect the filetype from application/octet-stream MIME type.",
    )
    return FileType.UNK


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
    if filename is not None:
        try:
            with open(filename, encoding=encoding) as f:
                file_text = f.read(4096)
        except UnicodeDecodeError:
            formatted_encoding, _ = detect_file_encoding(filename=filename)
            with open(filename, encoding=formatted_encoding) as f:
                file_text = f.read(4096)
    return file_text


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
        json.loads(file_text)
        return True
    except json.JSONDecodeError:
        return False


def is_json_processable(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    file_text: Optional[str] = None,
    encoding: Optional[str] = "utf-8",
) -> bool:
    exactly_one(filename=filename, file=file, file_text=file_text)
    if file_text is None:
        file_text = _read_file_start_for_type_check(
            file=file,
            filename=filename,
            encoding=encoding,
        )
    return re.match(LIST_OF_DICTS_PATTERN, file_text) is not None


def _count_commas(text: str):
    """Counts the number of commas in a line, excluding commas in quotes."""
    pattern = r"(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$),"
    matches = re.findall(pattern, text)
    return len(matches)


def _is_text_file_a_csv(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    encoding: Optional[str] = "utf-8",
):
    """Detects if a file that has a text/plain MIME type is a CSV file."""
    file_text = _read_file_start_for_type_check(
        file=file,
        filename=filename,
        encoding=encoding,
    )
    lines = file_text.strip().splitlines()
    if len(lines) < 2:
        return False
    lines = lines[: len(lines)] if len(lines) < 10 else lines[:10]
    header_count = _count_commas(lines[0])
    if any("," not in line for line in lines):
        return False
    return all(_count_commas(line) == header_count for line in lines[1:])


def _check_eml_from_buffer(file: IO[bytes]) -> bool:
    """Checks if a text/plain file is actually a .eml file. Uses a regex pattern to see if the
    start of the file matches the typical pattern for a .eml file."""
    file.seek(0)
    file_content = file.read(4096)
    if isinstance(file_content, bytes):
        file_head = file_content.decode("utf-8", errors="ignore")
    else:
        file_head = file_content
    return EMAIL_HEAD_RE.match(file_head) is not None


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


def _is_code_mime_type(mime_type: str) -> bool:
    """Checks to see if the MIME type is a MIME type that would be used for a code
    file."""
    mime_type = mime_type.lower()
    # NOTE(robinson) - check this one explicitly to avoid conflicts with other
    # MIME types that contain "go"
    if mime_type == "text/x-go":
        return True
    return any(language in mime_type for language in PROGRAMMING_LANGUAGES)


_P = ParamSpec("_P")


def add_metadata(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> List[Element]:
        elements = func(*args, **kwargs)
        sig = inspect.signature(func)
        params: Dict[str, Any] = dict(**dict(zip(sig.parameters, args)), **kwargs)
        for param in sig.parameters.values():
            if param.name not in params and param.default is not param.empty:
                params[param.name] = param.default
        include_metadata = params.get("include_metadata", True)
        if include_metadata:
            if params.get("metadata_filename"):
                params["filename"] = params.get("metadata_filename")

            metadata_kwargs = {
                kwarg: params.get(kwarg) for kwarg in ("filename", "url", "text_as_html")
            }
            # NOTE (yao): do not use cast here as cast(None) still is None
            if not str(kwargs.get("model_name", "")).startswith("chipper"):
                # NOTE(alan): Skip hierarchy if using chipper, as it should take care of that
                elements = set_element_hierarchy(elements)

            for element in elements:
                # NOTE(robinson) - Attached files have already run through this logic
                # in their own partitioning function
                if element.metadata.attached_to_filename is None:
                    _add_element_metadata(
                        element,
                        **metadata_kwargs,  # type: ignore
                    )

            return elements
        else:
            return _remove_element_metadata(
                elements,
            )

    return wrapper


def add_filetype(
    filetype: FileType,
) -> Callable[[Callable[_P, List[Element]]], Callable[_P, List[Element]]]:
    """..."""

    def decorator(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> List[Element]:
            elements = func(*args, **kwargs)
            sig = inspect.signature(func)
            params: Dict[str, Any] = dict(**dict(zip(sig.parameters, args)), **kwargs)
            for param in sig.parameters.values():
                if param.name not in params and param.default is not param.empty:
                    params[param.name] = param.default
            include_metadata = params.get("include_metadata", True)
            if include_metadata:
                if params.get("metadata_filename"):
                    params["filename"] = params.get("metadata_filename")

                for element in elements:
                    # NOTE(robinson) - Attached files have already run through this logic
                    # in their own partitioning function
                    if element.metadata.attached_to_filename is None:
                        _add_element_metadata(
                            element,
                            filetype=FILETYPE_TO_MIMETYPE[filetype],
                        )

                return elements
            else:
                return _remove_element_metadata(
                    elements,
                )

        return wrapper

    return decorator


def add_metadata_with_filetype(
    filetype: FileType,
) -> Callable[[Callable[_P, List[Element]]], Callable[_P, List[Element]]]:
    """..."""

    def decorator(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
        return add_filetype(filetype=filetype)(add_metadata(func))

    return decorator
