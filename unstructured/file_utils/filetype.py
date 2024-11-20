"""Automatically detect file-type based on inspection of the file's contents.

Auto-detection proceeds via a sequence of strategies. The first strategy to confidently determine a
file-type returns that value. A strategy that is not applicable, either because it lacks the input
required or fails to determine a file-type, returns `None` and execution continues with the next
strategy.

`_FileTypeDetector` is the main object and implements the three strategies.

The three strategies are:

- Use MIME-type asserted by caller in the `content_type` argument.
- Guess a MIME-type using libmagic, falling back to the `filetype` package when libmagic is
  unavailable.
- Map filename-extension to a `FileType` member.

A file that fails all three strategies is assigned the value `FileType.UNK`, for "unknown".

`_FileTypeDetectionContext` encapsulates the various arguments received by `detect_filetype()` and
provides values derived from them. This object is immutable and can be passed to delegates of
`_FileTypeDetector` to provide whatever context they need on the current detection instance.

`_FileTypeDetector` delegates to _differentiator_ objects like `_ZipFileDifferentiator` for
specialized discrimination and/or confirmation of ambiguous or frequently mis-identified
MIME-types. Additional differentiators are planned, one for `application/x-ole-storage`
(DOC, PPT, XLS, and MSG file-types) and perhaps others.
"""

from __future__ import annotations

import contextlib
import functools
import importlib.util
import json
import os
import re
import zipfile
from typing import IO, Callable, Iterator, Optional

import filetype as ft
from olefile import OleFileIO
from oxmsg.storage import Storage
from typing_extensions import ParamSpec

from unstructured.documents.elements import Element
from unstructured.file_utils.encoding import detect_file_encoding, format_encoding_str
from unstructured.file_utils.model import FileType
from unstructured.logger import logger
from unstructured.nlp.patterns import EMAIL_HEAD_RE, LIST_OF_DICTS_PATTERN
from unstructured.partition.common.common import add_element_metadata, exactly_one
from unstructured.partition.common.metadata import set_element_hierarchy
from unstructured.utils import get_call_args_applying_defaults, lazyproperty

LIBMAGIC_AVAILABLE = bool(importlib.util.find_spec("magic"))


def detect_filetype(
    file_path: str | None = None,
    file: IO[bytes] | None = None,
    encoding: str | None = None,
    content_type: str | None = None,
    metadata_file_path: Optional[str] = None,
) -> FileType:
    """Determine file-type of specified file using libmagic and/or fallback methods.

    One of `file_path` or `file` must be specified. A `file_path` that does not
    correspond to a file on the filesystem raises `ValueError`.

    Args:
        content_type: MIME-type of document-source, when already known. Providing
          a value for this argument disables auto-detection unless it does not map
          to a FileType member or is ambiguous, in which case it is ignored.
        encoding: Only used for textual file-types. When omitted, `utf-8` is
          assumed. Should generally be omitted except to resolve a problem with
          textual file-types like HTML.
        metadata_file_path: Only used when `file` is provided and then only as a
          source for a filename-extension that may be needed as a secondary
          content-type indicator. Ignored with the document is specified using
          `file_path`.

    Returns:
        A member of the `FileType` enumeration, `FileType.UNK` when the file type
        could not be determined or is not supported.

    Raises:
        ValueError: when:
        - `file_path` is specified but does not correspond to a file on the
          fileesystem.
        - Neither `file_path` nor `file` were specified.
    """
    ctx = _FileTypeDetectionContext.new(
        file_path=file_path,
        file=file,
        encoding=encoding,
        content_type=content_type,
        metadata_file_path=metadata_file_path,
    )
    return _FileTypeDetector.file_type(ctx)


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
        file_text = _FileTypeDetectionContext.new(
            file_path=filename, file=file, encoding=encoding
        ).text_head

    return re.match(LIST_OF_DICTS_PATTERN, file_text) is not None


class _FileTypeDetector:
    """Determines file type from a variety of possible inputs."""

    def __init__(self, ctx: _FileTypeDetectionContext):
        self._ctx = ctx

    @classmethod
    def file_type(cls, ctx: _FileTypeDetectionContext) -> FileType:
        """Detect file-type of document-source described by `ctx`."""
        return cls(ctx)._file_type

    @property
    def _file_type(self) -> FileType:
        """FileType member corresponding to this document source."""
        # -- strategy 1: use content-type asserted by caller --
        if file_type := self._file_type_from_content_type:
            return file_type

        # -- strategy 2: guess MIME-type using libmagic and use that --
        if file_type := self._file_type_from_guessed_mime_type:
            return file_type

        # -- strategy 3: use filename-extension, like ".docx" -> FileType.DOCX --
        if file_type := self._file_type_from_file_extension:
            return file_type

        # -- strategy 4: give up and report FileType.UNK --
        return FileType.UNK

    # == STRATEGIES ============================================================

    @property
    def _file_type_from_content_type(self) -> FileType | None:
        """Map passed content-type argument to a file-type, subject to certain rules."""
        content_type = self._ctx.content_type

        # -- when no content-type was asserted by caller, this strategy is not applicable --
        if not content_type:
            return None

        # -- OLE-based file-format content_type values are sometimes unreliable. These are
        # -- DOC, PPT, XLS, and MSG.
        if differentiator := _OleFileDifferentiator.applies(self._ctx, content_type):
            return differentiator.file_type

        # -- MS-Office 2007+ (OpenXML) content_type value is sometimes unreliable --
        if differentiator := _ZipFileDifferentiator.applies(self._ctx, content_type):
            return differentiator.file_type

        # -- otherwise we trust the passed `content_type` as long as `FileType` recognizes it --
        return FileType.from_mime_type(content_type)

    @property
    def _file_type_from_guessed_mime_type(self) -> FileType | None:
        """FileType based on auto-detection of MIME-type by libmagic.

        In some cases refinements are necessary on the magic-derived MIME-types. This process
        includes applying those rules, most of which are accumulated through practical experience.
        """
        mime_type = self._ctx.mime_type
        extension = self._ctx.extension

        # -- when libmagic is not installed, the `filetype` package is used instead.
        # -- `filetype.guess()` returns `None` for file-types it does not support, which
        # -- unfortunately includes all the textual file-types like CSV, EML, HTML, MD, RST, RTF,
        # -- TSV, and TXT. When we have no guessed MIME-type, this strategy is not applicable.
        if mime_type is None:
            return None

        if differentiator := _OleFileDifferentiator.applies(self._ctx, mime_type):
            return differentiator.file_type

        if mime_type.endswith("xml"):
            return FileType.HTML if extension in (".html", ".htm") else FileType.XML

        if differentiator := _TextFileDifferentiator.applies(self._ctx):
            return differentiator.file_type

        # -- applicable to "application/octet-stream", "application/zip", and all Office 2007+
        # -- document MIME-types, i.e. those for DOCX, PPTX, and XLSX. Note however it does NOT
        # -- apply to EPUB or ODT documents, even though those are also Zip archives. The zip and
        # -- octet-stream MIME-types are fed in because they are ambiguous. The MS-Office types are
        # -- differentiated because they are sometimes mistaken for each other, like DOCX mime-type
        # -- is actually a PPTX file etc.
        if differentiator := _ZipFileDifferentiator.applies(self._ctx, mime_type):
            return differentiator.file_type

        # -- All source-code files (e.g. *.py, *.js) are classified as plain text for the moment --
        if self._ctx.has_code_mime_type:
            return FileType.TXT

        if mime_type.endswith("empty"):
            return FileType.EMPTY

        # -- if no more-specific rules apply, use the MIME-type -> FileType mapping when present --
        if file_type := FileType.from_mime_type(mime_type):
            return file_type

        logger.warning(
            f"The MIME type{f' of {self._ctx.file_path!r}' if self._ctx.file_path else ''} is"
            f" {mime_type!r}. This file type is not currently supported in unstructured.",
        )
        return None

    @lazyproperty
    def _file_type_from_file_extension(self) -> FileType | None:
        """Determine file-type from filename extension.

        Returns `None` when no filename is available or when the extension does not map to a
        supported file-type.
        """
        return FileType.from_extension(self._ctx.extension)


class _FileTypeDetectionContext:
    """Provides all arguments to auto-file detection and values derived from them.

    This keeps computation of derived values out of the file-detection code but more importantly
    allows the main filetype-detector to pass the full context to any delegates without coupling
    itself to which values it might need.
    """

    def __init__(
        self,
        file_path: str | None = None,
        *,
        file: IO[bytes] | None = None,
        encoding: str | None = None,
        content_type: str | None = None,
        metadata_file_path: str | None = None,
    ):
        self._file_path_arg = file_path
        self._file_arg = file
        self._encoding_arg = encoding
        self._content_type = content_type
        self._metadata_file_path = metadata_file_path

    @classmethod
    def new(
        cls,
        *,
        file_path: str | None,
        file: IO[bytes] | None,
        encoding: str | None,
        content_type: str | None = None,
        metadata_file_path: str | None = None,
    ) -> _FileTypeDetectionContext:
        self = cls(
            file_path=file_path,
            file=file,
            encoding=encoding,
            content_type=content_type,
            metadata_file_path=metadata_file_path,
        )
        self._validate()
        return self

    @lazyproperty
    def content_type(self) -> str | None:
        """MIME-type asserted by caller; not based on inspection of file by this process.

        Would commonly occur when the file was downloaded via HTTP and a `"Content-Type:` header was
        present on the response. These are often ambiguous and sometimes just wrong so get some
        further verification. All lower-case when not `None`.
        """
        return self._content_type.lower() if self._content_type else None

    @lazyproperty
    def encoding(self) -> str:
        """Character-set used to encode text of this file.

        Relevant for textual file-types only, like HTML, TXT, JSON, etc.
        """
        return format_encoding_str(self._encoding_arg or "utf-8")

    @lazyproperty
    def extension(self) -> str:
        """Best filename-extension we can muster, "" when there is no available source."""
        # -- get from file_path, or file when it has a name (path) --
        with self.open() as file:
            if hasattr(file, "name") and file.name:
                return os.path.splitext(file.name)[1].lower()

        # -- otherwise use metadata file-path when provided --
        if file_path := self._metadata_file_path:
            return os.path.splitext(file_path)[1].lower()

        # -- otherwise empty str means no extension, same as a path like "a/b/name-no-ext" --
        return ""

    @lazyproperty
    def file_head(self) -> bytes:
        """The initial bytes of the file to be recognized, for use with libmagic detection."""
        with self.open() as file:
            return file.read(8192)

    @lazyproperty
    def file_path(self) -> str | None:
        """Filesystem path to file to be inspected, when provided on call.

        None when the caller specified the source as a file-like object instead. Useful for user
        feedback on an error, but users of context should have little use for it otherwise.
        """
        if (file_path := self._file_path_arg) is None:
            return None

        return os.path.realpath(file_path) if os.path.islink(file_path) else file_path

    @lazyproperty
    def is_zipfile(self) -> bool:
        """True when file is a Zip archive."""
        with self.open() as file:
            return zipfile.is_zipfile(file)

    @lazyproperty
    def has_code_mime_type(self) -> bool:
        """True when `mime_type` plausibly indicates a programming language source-code file."""
        mime_type = self.mime_type

        if mime_type is None:
            return False

        # -- check Go separately to avoid matching other MIME type containing "go" --
        if mime_type == "text/x-go":
            return True

        return any(
            lang in mime_type
            for lang in "c# c++ cpp csharp java javascript php python ruby swift typescript".split()
        )

    @lazyproperty
    def mime_type(self) -> str | None:
        """The best MIME-type we can get from `magic` (or `filetype` package).

        A `str` return value is always in lower-case.
        """
        file_path = self.file_path

        if LIBMAGIC_AVAILABLE:
            import magic

            mime_type = (
                magic.from_file(file_path, mime=True)
                if file_path
                else magic.from_buffer(self.file_head, mime=True)
            )
            return mime_type.lower() if mime_type else None

        mime_type = ft.guess_mime(file_path) if file_path else ft.guess_mime(self.file_head)

        if mime_type is None:
            logger.warning(
                "libmagic is unavailable but assists in filetype detection. Please consider"
                " installing libmagic for better results."
            )
            return None

        return mime_type.lower()

    @contextlib.contextmanager
    def open(self) -> Iterator[IO[bytes]]:
        """Encapsulates complexity of dealing with file-path or file-like-object.

        Provides an `IO[bytes]` object as the "common-denominator" document source.

        Must be used as a context manager using a `with` statement:

            with self._file as file:
                do things with file

        File is guaranteed to be at read position 0 when called.
        """
        if self.file_path:
            with open(self.file_path, "rb") as f:
                yield f
        else:
            file = self._file_arg
            assert file is not None  # -- guaranteed by `._validate()` --
            file.seek(0)
            yield file

    @lazyproperty
    def text_head(self) -> str:
        """The initial characters of the text file for use with text-format differentiation.

        Raises:
            UnicodeDecodeError if file cannot be read as text.
        """
        # TODO: only attempts fallback character-set detection for file-path case, not for
        # file-like object case. Seems like we should do both.

        if file := self._file_arg:
            file.seek(0)
            content = file.read(4096)
            file.seek(0)
            return (
                content
                if isinstance(content, str)
                else content.decode(encoding=self.encoding, errors="ignore")
            )

        file_path = self.file_path
        assert file_path is not None  # -- guaranteed by `._validate` --

        try:
            with open(file_path, encoding=self.encoding) as f:
                return f.read(4096)
        except UnicodeDecodeError:
            encoding, _ = detect_file_encoding(filename=file_path)
            with open(file_path, encoding=encoding) as f:
                return f.read(4096)

    def _validate(self) -> None:
        """Raise if the context is invalid."""
        if self.file_path and not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"no such file {self._file_path_arg}")
        if not self.file_path and not self._file_arg:
            raise ValueError("either `file_path` or `file` argument must be provided")


class _OleFileDifferentiator:
    """Refine an OLE-storage package (CFBF) file-type that may not be as specific as it could be.

    Compound File Binary Format (CFBF), aka. OLE file, is use by Microsoft for legacy MS Office
    files (DOC, PPT, XLS) as well as for Outlook MSG files. `libmagic` tends to identify these as
    `"application/x-ole-storage"` which is true but too not specific enough for partitioning
    purposes.
    """

    def __init__(self, ctx: _FileTypeDetectionContext):
        self._ctx = ctx

    @classmethod
    def applies(
        cls, ctx: _FileTypeDetectionContext, mime_type: str
    ) -> _OleFileDifferentiator | None:
        """Constructs an instance, but only if this differentiator applies for `mime_type`."""
        return cls(ctx) if cls._is_ole_file(ctx) else None

    @property
    def file_type(self) -> FileType | None:
        """Differentiated file-type for Microsoft Compound File Binary Format (CFBF).

        Returns one of:
        - `FileType.DOC`
        - `FileType.PPT`
        - `FileType.XLS`
        - `FileType.MSG`
        """
        # -- if this is not a CFBF file then whatever MIME-type was guessed is wrong, so return
        # -- `None` to trigger fall-back to next strategy.
        if not self._is_ole_file(self._ctx):
            return None

        # -- check storage contents of the ole file for file type markers
        if (ole_file_type := self._check_ole_file_type(self._ctx)) is not None:
            return ole_file_type

        # -- `filetype` lib is better at legacy MS-Office files than `libmagic`, so we rely on it
        # -- to differentiate those. Note `filetype` doesn't detect MSG type and won't always
        # -- detect DOC, PPT, or XLS, returning `None` instead. We let those fall through and we
        # -- rely on filename-extension to identify those.
        with self._ctx.open() as file:
            mime_type = ft.guess_mime(file)

        return FileType.from_mime_type(mime_type) if mime_type else None

    @staticmethod
    def _is_ole_file(ctx: _FileTypeDetectionContext) -> bool:
        """True when file has CFBF magic first 8 bytes."""
        with ctx.open() as file:
            return file.read(8) == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

    @staticmethod
    def _check_ole_file_type(ctx: _FileTypeDetectionContext) -> FileType | None:
        with ctx.open() as f:
            ole = OleFileIO(f)  # pyright: ignore[reportUnknownVariableType]
            root_storage = Storage.from_ole(ole)  # pyright: ignore[reportUnknownMemberType]

        for stream in root_storage.streams:
            if stream.name == "WordDocument":
                return FileType.DOC
            elif stream.name == "PowerPoint Document":
                return FileType.PPT
            elif stream.name == "Workbook":
                return FileType.XLS
            elif stream.name == "__properties_version1.0":
                return FileType.MSG

        return None


class _TextFileDifferentiator:
    """Refine a textual file-type that may not be as specific as it could be."""

    def __init__(self, ctx: _FileTypeDetectionContext):
        self._ctx = ctx

    @classmethod
    def applies(cls, ctx: _FileTypeDetectionContext) -> _TextFileDifferentiator | None:
        """Constructs an instance, but only if this differentiator applies in `ctx`."""
        mime_type = ctx.mime_type
        return (
            cls(ctx)
            if mime_type and (mime_type == "message/rfc822" or mime_type.startswith("text"))
            else None
        )

    @lazyproperty
    def file_type(self) -> FileType:
        """Differentiated file-type for textual content.

        Always produces a file-type, worst case that's `FileType.TXT` when nothing more specific
        applies.
        """
        extension = self._ctx.extension

        if extension in ".csv .eml .html .json .md .org .p7s .rst .rtf .tab .tsv".split():
            return FileType.from_extension(extension) or FileType.TXT

        # NOTE(crag): for older versions of the OS libmagic package, such as is currently
        # installed on the Unstructured docker image, .json files resolve to "text/plain"
        # rather than "application/json". this corrects for that case.
        if self._is_json:
            return FileType.JSON

        if self._is_csv:
            return FileType.CSV

        if self._is_eml:
            return FileType.EML

        if extension in (".text", ".txt"):
            return FileType.TXT

        # Safety catch
        if file_type := FileType.from_mime_type(self._ctx.mime_type):
            return file_type

        return FileType.TXT

    @lazyproperty
    def _is_csv(self) -> bool:
        """True when file is plausibly in Comma Separated Values (CSV) format."""

        def count_commas(text: str):
            """Counts the number of commas in a line, excluding commas in quotes."""
            pattern = r"(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$),"
            matches = re.findall(pattern, text)
            return len(matches)

        lines = self._ctx.text_head.strip().splitlines()
        if len(lines) < 2:
            return False
        # -- check at most the first 10 lines --
        lines = lines[: len(lines)] if len(lines) < 10 else lines[:10]
        # -- any lines without at least one comma disqualifies the file --
        if any("," not in line for line in lines):
            return False
        header_count = count_commas(lines[0])
        return all(count_commas(line) == header_count for line in lines[1:])

    @lazyproperty
    def _is_eml(self) -> bool:
        """Checks if a text/plain file is actually a .eml file.

        Uses a regex pattern to see if the start of the file matches the typical pattern for a .eml
        file.
        """
        return EMAIL_HEAD_RE.match(self._ctx.text_head) is not None

    @lazyproperty
    def _is_json(self) -> bool:
        """True when file is JSON collection.

        A JSON file that contains only a string, number, or boolean, while valid JSON, will fail
        this test since it is not partitionable.
        """
        text_head = self._ctx.text_head

        # -- an empty file is not JSON --
        if not text_head.lstrip():
            return False

        # -- has to be a list or object, no string, number, or bool --
        if text_head.lstrip()[0] not in "[{":
            return False

        try:
            with self._ctx.open() as file:
                json.load(file)
            return True
        except json.JSONDecodeError:
            return False


class _ZipFileDifferentiator:
    """Refine a Zip-packaged file-type that may be ambiguous or swapped."""

    def __init__(self, ctx: _FileTypeDetectionContext):
        self._ctx = ctx

    @classmethod
    def applies(
        cls, ctx: _FileTypeDetectionContext, mime_type: str
    ) -> _ZipFileDifferentiator | None:
        """Constructs an instance, but only if this differentiator applies for `mime_type`.

        Separate `mime_type` argument allows it to be applied to either asserted content-type or
        guessed mime-type.
        """
        return (
            cls(ctx)
            if mime_type
            in (
                "application/octet-stream",
                "application/zip",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            else None
        )

    @lazyproperty
    def file_type(self) -> FileType | None:
        """Differentiated file-type for a Zip archive.

        Returns `None` if the file is not a Zip archive. Otherwise it returns `FileType.DOCX`,
        `FileType.PPTX`, or `FileType.XLSX` when one of those applies and `FileType.ZIP` otherwise.
        """
        if not self._ctx.is_zipfile:
            return None

        with self._ctx.open() as file:
            zip = zipfile.ZipFile(file)

            # NOTE(robinson) - .docx and .xlsx files are actually a zip file with a .docx/.xslx
            # extension. If the MIME type is application/octet-stream, we check if it's a
            # .docx/.xlsx file by looking for expected filenames within the zip file.
            filenames = [f.filename for f in zip.filelist]

            if all(f in filenames for f in ("word/document.xml",)):
                return FileType.DOCX

            if all(f in filenames for f in ("xl/workbook.xml",)):
                return FileType.XLSX

            if all(f in filenames for f in ("ppt/presentation.xml",)):
                return FileType.PPTX

        return FileType.ZIP


_P = ParamSpec("_P")


def add_metadata(func: Callable[_P, list[Element]]) -> Callable[_P, list[Element]]:
    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> list[Element]:
        elements = func(*args, **kwargs)
        call_args = get_call_args_applying_defaults(func, *args, **kwargs)

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

    return wrapper


def add_filetype(
    filetype: FileType,
) -> Callable[[Callable[_P, list[Element]]], Callable[_P, list[Element]]]:
    """Post-process element-metadata for list[Element] from partitioning.

    This decorator adds a post-processing step to a document partitioner.

    - Adds `.metadata.filetype` (source-document MIME-type) metadata value

    This "partial" decorator is present because `partition_image()` does not apply
    `.metadata.filetype` this way since each image type has its own MIME-type (e.g. `image.jpeg`,
    `image/png`, etc.).
    """

    def decorator(func: Callable[_P, list[Element]]) -> Callable[_P, list[Element]]:
        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> list[Element]:
            elements = func(*args, **kwargs)

            for element in elements:
                # NOTE(robinson) - Attached files have already run through this logic
                # in their own partitioning function
                if element.metadata.attached_to_filename is None:
                    add_element_metadata(element, filetype=filetype.mime_type)

            return elements

        return wrapper

    return decorator


def add_metadata_with_filetype(
    filetype: FileType,
) -> Callable[[Callable[_P, list[Element]]], Callable[_P, list[Element]]]:
    """..."""

    def decorator(func: Callable[_P, list[Element]]) -> Callable[_P, list[Element]]:
        return add_filetype(filetype=filetype)(add_metadata(func))

    return decorator
