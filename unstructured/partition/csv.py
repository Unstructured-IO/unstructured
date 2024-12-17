from __future__ import annotations

import contextlib
import csv
from typing import IO, Any, Iterator

import pandas as pd

from unstructured.chunking import add_chunking_strategy
from unstructured.common.html_table import HtmlTable
from unstructured.documents.elements import Element, ElementMetadata, Table
from unstructured.file_utils.model import FileType
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date
from unstructured.utils import is_temp_file_path, lazyproperty

DETECTION_ORIGIN: str = "csv"


@apply_metadata(FileType.CSV)
@add_chunking_strategy
def partition_csv(
    filename: str | None = None,
    *,
    file: IO[bytes] | None = None,
    encoding: str | None = None,
    include_header: bool = False,
    infer_table_structure: bool = True,
    **kwargs: Any,
) -> list[Element]:
    """Partitions Microsoft Excel Documents in .csv format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    include_header
        Determines whether or not header info info is included in text and medatada.text_as_html.
    infer_table_structure
        If True, any Table elements that are extracted will also have a metadata field
        named "text_as_html" where the table's text content is rendered into an html string.
        I.e., rows and cells are preserved.
        Whether True or False, the "text" field is always present in any Table element
        and is the text content of the table (no structure).
    """
    ctx = _CsvPartitioningContext.load(
        file_path=filename,
        file=file,
        encoding=encoding,
        include_header=include_header,
        infer_table_structure=infer_table_structure,
    )

    with ctx.open() as file:
        dataframe = pd.read_csv(file, header=ctx.header, sep=ctx.delimiter, encoding=encoding)

    html_table = HtmlTable.from_html_text(
        dataframe.to_html(index=False, header=include_header, na_rep="")
    )

    metadata = ElementMetadata(
        filename=filename,
        last_modified=ctx.last_modified,
        text_as_html=html_table.html if infer_table_structure else None,
    )

    # -- a CSV file becomes a single `Table` element --
    return [Table(text=html_table.text, metadata=metadata, detection_origin=DETECTION_ORIGIN)]


class _CsvPartitioningContext:
    """Encapsulates the partitioning-run details.

    Provides access to argument values and especially encapsulates computation of values derived
    from those values so they don't obscure the core partitioning logic.
    """

    def __init__(
        self,
        file_path: str | None = None,
        file: IO[bytes] | None = None,
        encoding: str | None = None,
        include_header: bool = False,
        infer_table_structure: bool = True,
    ):
        self._file_path = file_path
        self._file = file
        self._encoding = encoding
        self._include_header = include_header
        self._infer_table_structure = infer_table_structure

    @classmethod
    def load(
        cls,
        file_path: str | None,
        file: IO[bytes] | None,
        encoding: str | None,
        include_header: bool,
        infer_table_structure: bool,
    ) -> _CsvPartitioningContext:
        return cls(
            file_path=file_path,
            file=file,
            encoding=encoding,
            include_header=include_header,
            infer_table_structure=infer_table_structure,
        )._validate()

    @lazyproperty
    def delimiter(self) -> str | None:
        """The CSV delimiter, nominally a comma ",".

        `None` for a single-column CSV file which naturally has no delimiter.
        """
        sniffer = csv.Sniffer()
        num_bytes = 65536

        with self.open() as file:
            # -- read whole lines, sniffer can be confused by a trailing partial line --
            data = "\n".join(
                ln.decode(self._encoding or "utf-8") for ln in file.readlines(num_bytes)
            )

        try:
            return sniffer.sniff(data, delimiters=",;").delimiter
        except csv.Error:
            # -- sniffing will fail on single-column csv as no default can be assumed --
            return None

    @lazyproperty
    def header(self) -> int | None:
        """Identifies the header row, if any, to Pandas, by idx."""
        return 0 if self._include_header else None

    @lazyproperty
    def last_modified(self) -> str | None:
        """The best last-modified date available, None if no sources are available."""
        return (
            None
            if not self._file_path or is_temp_file_path(self._file_path)
            else get_last_modified_date(self._file_path)
        )

    @contextlib.contextmanager
    def open(self) -> Iterator[IO[bytes]]:
        """Encapsulates complexity of dealing with file-path or file-like-object.

        Provides an `IO[bytes]` object as the "common-denominator" document source.

        Must be used as a context manager using a `with` statement:

            with self._file as file:
                do things with file

        File is guaranteed to be at read position 0 when called.
        """
        if self._file_path:
            with open(self._file_path, "rb") as f:
                yield f
        else:
            file = self._file
            assert file is not None  # -- guaranteed by `._validate()` --
            # -- Be polite on principle. Reset file-pointer both before and after use --
            file.seek(0)
            yield file
            file.seek(0)

    def _validate(self) -> _CsvPartitioningContext:
        """Raise on invalid argument values."""
        if self._file_path is None and self._file is None:
            raise ValueError("either file-path or file-like object must be provided")
        return self
