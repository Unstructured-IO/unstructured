"""Domain-model for file-types."""

from __future__ import annotations

import enum
from typing import Iterable, cast


class FileType(enum.Enum):
    """The collection of file-types recognized by `unstructured`.

    Note not all of these can be partitioned, e.g. WAV and ZIP have no partitioner.
    """

    _extensions: tuple[str, ...]

    _canonical_mime_type: str
    """The MIME-type used as `.metadata.filetype` for this file-type."""

    _alias_mime_types: tuple[str, ...]
    """MIME-types accepted as identifying this file-type."""

    def __new__(
        cls,
        value: str,
        extensions: Iterable[str],
        canonical_mime_type: str,
        alias_mime_types: Iterable[str],
    ):
        self = object.__new__(cls)
        self._value_ = value
        self._extensions = tuple(extensions)
        self._canonical_mime_type = canonical_mime_type
        self._alias_mime_types = tuple(alias_mime_types)
        return self

    def __lt__(self, other: FileType) -> bool:
        """Makes `FileType` members comparable with relational operators, at least with `<`.

        This makes them sortable, in particular it supports sorting for pandas groupby functions.
        """
        return self.name < other.name

    BMP = ("bmp", [".bmp"], "image/bmp", cast(list[str], []))
    CSV = (
        "csv",
        [".csv"],
        "text/csv",
        [
            "application/csv",
            "application/x-csv",
            "text/comma-separated-values",
            "text/x-comma-separated-values",
            "text/x-csv",
        ],
    )
    DOC = ("doc", [".doc"], "application/msword", cast(list[str], []))
    DOCX = (
        "docx",
        [".docx"],
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        cast(list[str], []),
    )
    EML = ("eml", [".eml", ".p7s"], "message/rfc822", cast(list[str], []))
    EPUB = ("epub", [".epub"], "application/epub", ["application/epub+zip"])
    HEIC = ("heic", [".heic"], "image/heic", cast(list[str], []))
    HTML = ("html", [".html", ".htm"], "text/html", cast(list[str], []))
    JPG = ("jpg", [".jpeg", ".jpg"], "image/jpeg", cast(list[str], []))
    JSON = ("json", [".json"], "application/json", cast(list[str], []))
    MD = ("md", [".md"], "text/markdown", ["text/x-markdown"])
    MSG = ("msg", [".msg"], "application/vnd.ms-outlook", ["application/x-ole-storage"])
    ODT = ("odt", [".odt"], "application/vnd.oasis.opendocument.text", cast(list[str], []))
    ORG = ("org", [".org"], "text/org", cast(list[str], []))
    PDF = ("pdf", [".pdf"], "application/pdf", cast(list[str], []))
    PNG = ("png", [".png"], "image/png", cast(list[str], []))
    PPT = ("ppt", [".ppt"], "application/vnd.ms-powerpoint", cast(list[str], []))
    PPTX = (
        "pptx",
        [".pptx"],
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        cast(list[str], []),
    )
    RST = ("rst", [".rst"], "text/x-rst", cast(list[str], []))
    RTF = ("rtf", [".rtf"], "text/rtf", ["application/rtf"])
    TIFF = ("tiff", [".tiff"], "image/tiff", cast(list[str], []))
    TSV = ("tsv", [".tab", ".tsv"], "text/tsv", cast(list[str], []))
    TXT = (
        "txt",
        [
            ".txt",
            ".text",
            # NOTE(robinson) - for now we are treating code files as plain text
            ".c",
            ".cc",
            ".cpp",
            ".cs",
            ".cxx",
            ".go",
            ".java",
            ".js",
            ".log",
            ".php",
            ".py",
            ".rb",
            ".swift",
            ".ts",
            ".yaml",
            ".yml",
        ],
        "text/plain",
        [
            # NOTE(robinson) - In the future, we may have special processing for YAML files
            # instead of treating them as plaintext.
            "text/yaml",
            "application/x-yaml",
            "application/yaml",
            "text/x-yaml",
        ],
    )
    WAV = (
        "wav",
        [".wav"],
        "audio/wav",
        [
            "audio/vnd.wav",
            "audio/vnd.wave",
            "audio/wave",
            "audio/x-pn-wav",
            "audio/x-wav",
        ],
    )
    XLS = ("xls", [".xls"], "application/vnd.ms-excel", cast(list[str], []))
    XLSX = (
        "xlsx",
        [".xlsx"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        cast(list[str], []),
    )
    XML = ("xml", [".xml"], "application/xml", ["text/xml"])
    ZIP = ("zip", [".zip"], "application/zip", cast(list[str], []))

    UNK = ("unk", cast(list[str], []), "application/octet-stream", cast(list[str], []))
    EMPTY = ("empty", cast(list[str], []), "inode/x-empty", cast(list[str], []))

    @classmethod
    def from_extension(cls, extension: str | None) -> FileType | None:
        """Select a FileType member based on an extension.

        `extension` must include the leading period, like `".pdf"`. Extension is suitable as a
        secondary file-type identification method but is unreliable for primary identification..

        Returns `None` when `extension` is not registered for any supported file-type.
        """
        if extension in (None, "", "."):
            return None
        # -- not super efficient but plenty fast enough for once-or-twice-per-file use and avoids
        # -- limitations on defining a class variable on an Enum.
        for m in cls.__members__.values():
            if extension in m._extensions:
                return m
        return None

    @classmethod
    def from_mime_type(cls, mime_type: str) -> FileType | None:
        """Select a FileType member based on a MIME-type.

        `extension` must include the leading period, like `".pdf"`. Extension is suitable as a
        secondary file-type identification method but is unreliable for primary identification..
        """
        # -- not super efficient but plenty fast enough for once-or-twice-per-file use and avoids
        # -- limitations on defining a class variable on an Enum.
        for m in cls.__members__.values():
            if mime_type == m._canonical_mime_type or mime_type in m._alias_mime_types:
                return m
        return None

    @property
    def mime_type(self) -> str:
        """The canonical MIME-type for this file-type, suitable for use in metadata.

        This value is used in `.metadata.filetype` for elements partitioned from files of this
        type. In general it is the "offical", "recommended", or "defacto-standard" MIME-type for
        files of this type, in that order, as available.
        """
        return self._canonical_mime_type


PLAIN_TEXT_EXTENSIONS = ".csv .eml .html .json .md .org .p7s .rst .rtf .tab .text .tsv .txt".split()
