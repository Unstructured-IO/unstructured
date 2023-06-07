import inspect
import os
import re
import zipfile
from enum import Enum
from functools import wraps
from typing import IO, Callable, List, Optional

from unstructured.documents.elements import Element, PageBreak
from unstructured.nlp.patterns import LIST_OF_DICTS_PATTERN
from unstructured.partition.common import (
    _add_element_metadata,
    _remove_element_metadata,
    exactly_one,
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


class FileType(Enum):
    UNK = 0

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

    # Plain Text Types
    EML = 40
    RTF = 41
    TXT = 42
    JSON = 43
    CSV = 44

    # Markup Types
    HTML = 50
    XML = 51
    MD = 52
    EPUB = 53

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
    "text/plain": FileType.TXT,
    "text/x-csv": FileType.CSV,
    "application/csv": FileType.CSV,
    "application/x-csv": FileType.CSV,
    "text/comma-separated-values": FileType.CSV,
    "text/x-comma-separated-values": FileType.CSV,
    "text/csv": FileType.CSV,
    "text/markdown": FileType.MD,
    "text/x-markdown": FileType.MD,
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


def _resolve_symlink(file_path):
    # Resolve the symlink to get the actual file path
    if os.path.islink(file_path):
        file_path = os.path.realpath(file_path)
    return file_path


def detect_filetype(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO] = None,
    file_filename: Optional[str] = None,
) -> Optional[FileType]:
    """Use libmagic to determine a file's type. Helps determine which partition brick
    to use for a given file. A return value of None indicates a non-supported file type.
    """
    exactly_one(filename=filename, file=file)

    if content_type:
        filetype = STR_TO_FILETYPE.get(content_type)
        if filetype:
            return filetype

    if filename or file_filename:
        _filename = filename or file_filename or ""
        _, extension = os.path.splitext(_filename)
        extension = extension.lower()
        if os.path.isfile(_filename) and LIBMAGIC_AVAILABLE:
            mime_type = magic.from_file(
                _resolve_symlink(filename or file_filename),
                mime=True,
            )  # type: ignore
        else:
            return EXT_TO_FILETYPE.get(extension.lower(), FileType.UNK)

    elif file is not None:
        extension = None
        # NOTE(robinson) - the python-magic docs recommend reading at least the first 2048 bytes
        # Increased to 4096 because otherwise .xlsx files get detected as a zip file
        # ref: https://github.com/ahupp/python-magic#usage
        if LIBMAGIC_AVAILABLE:
            mime_type = magic.from_buffer(file.read(4096), mime=True)
        else:
            raise ImportError(
                "libmagic is unavailable. "
                "Filetype detection on file-like objects requires libmagic. "
                "Please install libmagic and try again.",
            )
    else:
        raise ValueError("No filename, file, nor file_filename were specified.")

    """Mime type special cases."""

    # NOTE(crag): for older versions of the OS libmagic package, such as is currently
    # installed on the Unstructured docker image, .json files resolve to "text/plain"
    # rather than "application/json". this corrects for that case.
    if mime_type == "text/plain" and extension == ".json":
        return FileType.JSON

    # NOTE(Crag): older magic lib does not differentiate between xls and doc
    if mime_type == "application/msword" and extension == ".xls":
        return FileType.XLS

    elif mime_type.endswith("xml"):
        if extension and (extension == ".html" or extension == ".htm"):
            return FileType.HTML
        else:
            return FileType.XML

    elif mime_type in TXT_MIME_TYPES or mime_type.startswith("text"):
        if extension and extension == ".eml":
            return FileType.EML
        elif extension and extension == ".md":
            return FileType.MD
        elif extension and extension == ".rtf":
            return FileType.RTF
        elif extension and extension == ".html":
            return FileType.HTML

        if _is_text_file_a_json(file=file, filename=filename):
            return FileType.JSON

        if file and not extension and _check_eml_from_buffer(file=file) is True:
            return FileType.EML

        # Safety catch
        if mime_type in STR_TO_FILETYPE:
            return STR_TO_FILETYPE[mime_type]

        return FileType.TXT

    elif mime_type == "application/octet-stream":
        if file and not extension:
            return _detect_filetype_from_octet_stream(file=file)
        else:
            return EXT_TO_FILETYPE.get(extension, FileType.UNK)

    elif mime_type == "application/zip":
        filetype = FileType.UNK
        if file and not extension:
            filetype = _detect_filetype_from_octet_stream(file=file)
        elif filename is not None:
            with open(filename, "rb") as f:
                filetype = _detect_filetype_from_octet_stream(file=f)

        extension = extension if extension else ""
        if filetype == FileType.UNK:
            return EXT_TO_FILETYPE.get(extension.lower(), FileType.ZIP)
        else:
            return EXT_TO_FILETYPE.get(extension.lower(), filetype)

    elif _is_code_mime_type(mime_type):
        # NOTE(robinson) - we'll treat all code files as plain text for now.
        # we can update this logic and add filetypes for specific languages
        # later if needed.
        return FileType.TXT

    # For everything else
    elif mime_type in STR_TO_FILETYPE:
        return STR_TO_FILETYPE[mime_type]

    logger.warning(
        f"The MIME type{f' of {filename!r}' if filename else ''} is {mime_type!r}. "
        "This file type is not currently supported in unstructured.",
    )
    return EXT_TO_FILETYPE.get(extension, FileType.UNK)


def _detect_filetype_from_octet_stream(file: IO) -> FileType:
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

    logger.warning(
        "Could not detect the filetype from application/octet-stream MIME type.",
    )
    return FileType.UNK


def _is_text_file_a_json(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO] = None,
):
    """Detects if a file that has a text/plain MIME type is a JSON file."""
    exactly_one(filename=filename, file=file)

    if file is not None:
        file.seek(0)
        file_content = file.read(4096)
        if isinstance(file_content, str):
            file_text = file_content
        else:
            file_text = file_content.decode(errors="ignore")
        file.seek(0)
    elif filename is not None:
        with open(filename) as f:
            file_text = f.read()

    return re.match(LIST_OF_DICTS_PATTERN, file_text) is not None


def _check_eml_from_buffer(file: IO) -> bool:
    """Checks if a text/plain file is actually a .eml file. Uses a regex pattern to see if the
    start of the file matches the typical pattern for a .eml file."""
    file.seek(0)
    file_content = file.read(4096)
    if isinstance(file_content, bytes):
        file_head = file_content.decode("utf-8", errors="ignore")
    else:
        file_head = file_content

    return EMAIL_HEAD_RE.match(file_head) is not None


def document_to_element_list(
    document,
    include_page_breaks: bool = False,
) -> List[Element]:
    """Converts a DocumentLayout object to a list of unstructured elements."""
    elements: List[Element] = []
    image_formats: List[str] = []
    num_pages = len(document.pages)
    for i, page in enumerate(document.pages):
        for element in page.elements:
            elements.append(element)
            if hasattr(page, "image"):
                image_formats.append(page.image.format)
        if include_page_breaks and i < num_pages - 1:
            elements.append(PageBreak())

    if image_formats and all(image_format == "PNG" for image_format in image_formats):
        filetype = FileType.PNG.name
    elif image_formats and all(image_format == "JPEG" for image_format in image_formats):
        filetype = FileType.JPG.name
    else:
        filetype = None
    elements = _add_element_metadata(
        elements,
        include_page_breaks=include_page_breaks,
        filetype=filetype,
    )
    return elements


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


def add_metadata_with_filetype(filetype: FileType):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elements = func(*args, **kwargs)
            sig = inspect.signature(func)
            params = dict(**dict(zip(sig.parameters, args)), **kwargs)
            for param in sig.parameters.values():
                if param.name not in params and param.default is not param.empty:
                    params[param.name] = param.default
            include_metadata = params.get("include_metadata", True)
            if include_metadata:
                metadata_kwargs = {
                    kwarg: params.get(kwarg) for kwarg in ("include_page_breaks", "filename", "url")
                }
                return _add_element_metadata(
                    elements,
                    filetype=FILETYPE_TO_MIMETYPE[filetype],
                    **metadata_kwargs,  # type: ignore
                )
            else:
                return _remove_element_metadata(
                    elements,
                )

        return wrapper

    return decorator
