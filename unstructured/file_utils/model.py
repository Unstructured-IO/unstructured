"""Domain-model for file-types."""

from __future__ import annotations

import enum
from typing import Iterable, cast


class FileType(enum.Enum):
    """The collection of file-types recognized by `unstructured`.

    Note not all of these can be partitioned, e.g. WAV and ZIP have no partitioner.
    """

    _partitioner_shortname: str | None
    """Like "docx", from which partitioner module and function-name can be derived via template."""

    _importable_package_dependencies: tuple[str, ...]
    """Packages that must be available for import for this file-type's partitioner to work."""

    _extra_name: str | None
    """`pip install` extra that provides package dependencies for this file-type."""

    _extensions: tuple[str, ...]
    """Filename-extensions recognized as this file-type. Use for secondary identification only."""

    _canonical_mime_type: str
    """The MIME-type used as `.metadata.filetype` for this file-type."""

    _alias_mime_types: tuple[str, ...]
    """MIME-types accepted as identifying this file-type."""

    def __new__(
        cls,
        value: str,
        partitioner_shortname: str | None,
        importable_package_dependencies: Iterable[str],
        extra_name: str | None,
        extensions: Iterable[str],
        canonical_mime_type: str,
        alias_mime_types: Iterable[str],
    ):
        self = object.__new__(cls)
        self._value_ = value
        self._partitioner_shortname = partitioner_shortname
        self._importable_package_dependencies = tuple(importable_package_dependencies)
        self._extra_name = extra_name
        self._extensions = tuple(extensions)
        self._canonical_mime_type = canonical_mime_type
        self._alias_mime_types = tuple(alias_mime_types)
        return self

    def __lt__(self, other: FileType) -> bool:
        """Makes `FileType` members comparable with relational operators, at least with `<`.

        This makes them sortable, in particular it supports sorting for pandas groupby functions.
        """
        return self.name < other.name

    @classmethod
    def from_extension(cls, extension: str | None) -> FileType | None:
        """Select a FileType member based on an extension.

        `extension` must include the leading period, like `".pdf"`. Extension is suitable as a
        secondary file-type identification method but is unreliable for primary identification.

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
    def from_mime_type(cls, mime_type: str | None) -> FileType | None:
        """Select a FileType member based on a MIME-type.

        Returns `None` when `mime_type` is `None` or does not map to the canonical MIME-type of a
        `FileType` member or one of its alias MIME-types.
        """
        if mime_type is None:
            return None
        # -- not super efficient but plenty fast enough for once-or-twice-per-file use and avoids
        # -- limitations on defining a class variable on an Enum.
        for m in cls.__members__.values():
            if mime_type == m._canonical_mime_type or mime_type in m._alias_mime_types:
                return m
        return None

    @property
    def extra_name(self) -> str | None:
        """The `pip` "extra" that must be installed to provide this file-type's dependencies.

        Like "image" for PNG, as in `pip install "unstructured[image]"`.

        `None` when partitioning this file-type requires only the base `unstructured` install.
        """
        return self._extra_name

    @property
    def importable_package_dependencies(self) -> tuple[str, ...]:
        """Packages that must be importable for this file-type's partitioner to work.

        In general, these are the packages provided by the `pip install` "extra" for this file-type,
        like `pip install "unstructured[docx]"` loads the `python-docx` package.

        Note that these names are the ones used in an `import` statement, which is not necessarily
        the same as the _distribution_ package name used by `pip`. For example, the DOCX
        distribution package name is `"python-docx"` whereas the _importable_ package name is
        `"docx"`. This latter name as it appears like `import docx` is what is provided by this
        property.

        The return value is an empty tuple for file-types that do not require optional dependencies.

        Note this property does not complain when accessed on a non-partitionable file-type, it
        simply returns an empty tuple because file-types that are not partitionable require no
        optional dependencies.
        """
        return self._importable_package_dependencies

    @property
    def is_partitionable(self) -> bool:
        """True when there is a partitioner for this file-type.

        Note this does not check whether the dependencies for this file-type are installed so
        attempting to partition a file of this type may still fail. This is meant for
        distinguishing file-types like WAV, ZIP, EMPTY, and UNK which are legitimate file-types
        but have no associated partitioner.
        """
        return bool(self._partitioner_shortname)

    @property
    def mime_type(self) -> str:
        """The canonical MIME-type for this file-type, suitable for use in metadata.

        This value is used in `.metadata.filetype` for elements partitioned from files of this
        type. In general it is the "offical", "recommended", or "defacto-standard" MIME-type for
        files of this type, in that order, as available.
        """
        return self._canonical_mime_type

    @property
    def partitioner_function_name(self) -> str:
        """Name of partitioner function for this file-type. Like "partition_docx".

        Raises when this property is accessed on a file-type that is not partitionable. Use
        `.is_partitionable` to avoid exceptions when partitionability is unknown.
        """
        # -- Raise when this property is accessed on a FileType member that has no partitioner
        # -- shortname. This prevents a harder-to-find bug from appearing far away from this call
        # -- when code would try to `getattr(module, None)` or whatever.
        if (shortname := self._partitioner_shortname) is None:
            raise ValueError(
                f"`.partitioner_function_name` is undefined because FileType.{self.name} is not"
                f" partitionable. Use `.is_partitionable` to determine whether a `FileType`"
                f" is partitionable."
            )
        return f"partition_{shortname}"

    @property
    def partitioner_module_qname(self) -> str:
        """Fully-qualified name of module providing partitioner for this file-type.

        e.g. "unstructured.partition.docx" for FileType.DOCX.
        """
        # -- Raise when this property is accessed on a FileType member that has no partitioner
        # -- shortname. This prevents a harder-to-find bug from appearing far away from this call
        # -- when code would try to `importlib.import_module(None)` or whatever.
        if (shortname := self._partitioner_shortname) is None:
            raise ValueError(
                f"`.partitioner_module_qname` is undefined because FileType.{self.name} is not"
                f" partitionable. Use `.is_partitionable` to determine whether a `FileType`"
                f" is partitionable."
            )
        return f"unstructured.partition.{shortname}"

    @property
    def partitioner_shortname(self) -> str | None:
        """Familiar name of partitioner, like "image" for file-types that use `partition_image()`.

        One use is to determine whether a file-type is one of the five image types, all of which
        are processed by `partition_image()`.

        `None` for file-types that are not partitionable, although `.is_partitionable` is the
        preferred way of discovering that.
        """
        return self._partitioner_shortname

    BMP = (
        "bmp",  # -- value for this Enum member, like BMP = "bmp" in a simple enum --
        "image",  # -- partitioner_shortname --
        ["unstructured_inference"],  # -- importable_package_dependencies --
        "image",  # -- extra_name - like `pip install "unstructured[image]"` in this case --
        [".bmp"],  # -- extensions - filename extensions that map to this file-type --
        "image/bmp",  # -- canonical_mime_type -  MIME-type written to `.metadata.filetype` --
        cast(list[str], []),  # -- alias_mime-types - other MIME-types that map to this file-type --
    )
    CSV = (
        "csv",
        "csv",
        ["pandas"],
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
    DOC = ("doc", "doc", ["docx"], "doc", [".doc"], "application/msword", cast(list[str], []))
    DOCX = (
        "docx",
        "docx",
        ["docx"],
        "docx",
        [".docx"],
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        cast(list[str], []),
    )
    EML = (
        "eml",
        "email",
        cast(list[str], []),
        None,
        [".eml", ".p7s"],
        "message/rfc822",
        cast(list[str], []),
    )
    EPUB = (
        "epub",
        "epub",
        ["pypandoc"],
        "epub",
        [".epub"],
        "application/epub",
        ["application/epub+zip"],
    )
    HEIC = (
        "heic",
        "image",
        ["unstructured_inference"],
        "image",
        [".heic"],
        "image/heic",
        cast(list[str], []),
    )
    HTML = (
        "html",
        "html",
        cast(list[str], []),
        None,
        [".html", ".htm"],
        "text/html",
        cast(list[str], []),
    )
    JPG = (
        "jpg",
        "image",
        ["unstructured_inference"],
        "image",
        [".jpeg", ".jpg"],
        "image/jpeg",
        cast(list[str], []),
    )
    JSON = (
        "json",
        "json",
        cast(list[str], []),
        None,
        [".json"],
        "application/json",
        cast(list[str], []),
    )
    MD = ("md", "md", ["markdown"], "md", [".md"], "text/markdown", ["text/x-markdown"])
    MSG = (
        "msg",
        "msg",
        ["oxmsg"],
        "msg",
        [".msg"],
        "application/vnd.ms-outlook",
        cast(list[str], []),
    )
    ODT = (
        "odt",
        "odt",
        ["docx", "pypandoc"],
        "odt",
        [".odt"],
        "application/vnd.oasis.opendocument.text",
        cast(list[str], []),
    )
    ORG = ("org", "org", ["pypandoc"], "org", [".org"], "text/org", cast(list[str], []))
    PDF = (
        "pdf",
        "pdf",
        ["pdf2image", "pdfminer", "PIL"],
        "pdf",
        [".pdf"],
        "application/pdf",
        cast(list[str], []),
    )
    PNG = (
        "png",
        "image",
        ["unstructured_inference"],
        "image",
        [".png"],
        "image/png",
        cast(list[str], []),
    )
    PPT = (
        "ppt",
        "ppt",
        ["pptx"],
        "ppt",
        [".ppt"],
        "application/vnd.ms-powerpoint",
        cast(list[str], []),
    )
    PPTX = (
        "pptx",
        "pptx",
        ["pptx"],
        "pptx",
        [".pptx"],
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        cast(list[str], []),
    )
    RST = ("rst", "rst", ["pypandoc"], "rst", [".rst"], "text/x-rst", cast(list[str], []))
    RTF = ("rtf", "rtf", ["pypandoc"], "rtf", [".rtf"], "text/rtf", ["application/rtf"])
    TIFF = (
        "tiff",
        "image",
        ["unstructured_inference"],
        "image",
        [".tiff"],
        "image/tiff",
        cast(list[str], []),
    )
    TSV = ("tsv", "tsv", ["pandas"], "tsv", [".tab", ".tsv"], "text/tsv", cast(list[str], []))
    TXT = (
        "txt",
        "text",
        cast(list[str], []),
        None,
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
        None,
        cast(list[str], []),
        None,
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
    XLS = (
        "xls",
        "xlsx",
        ["pandas", "openpyxl"],
        "xlsx",
        [".xls"],
        "application/vnd.ms-excel",
        cast(list[str], []),
    )
    XLSX = (
        "xlsx",
        "xlsx",
        ["pandas", "openpyxl"],
        "xlsx",
        [".xlsx"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        cast(list[str], []),
    )
    XML = ("xml", "xml", cast(list[str], []), None, [".xml"], "application/xml", ["text/xml"])
    ZIP = ("zip", None, cast(list[str], []), None, [".zip"], "application/zip", cast(list[str], []))

    UNK = (
        "unk",
        None,
        cast(list[str], []),
        None,
        cast(list[str], []),
        "application/octet-stream",
        cast(list[str], []),
    )
    EMPTY = (
        "empty",
        None,
        cast(list[str], []),
        None,
        cast(list[str], []),
        "inode/x-empty",
        cast(list[str], []),
    )
