from __future__ import annotations

import codecs
import contextlib
import csv
import itertools
from functools import cached_property
from typing import IO, Any, Iterator

import pandas as pd

from unstructured.chunking import add_chunking_strategy
from unstructured.common.html_table import HtmlTable
from unstructured.documents.elements import Element, ElementMetadata, Table
from unstructured.errors import UnprocessableEntityError
from unstructured.file_utils.model import FileType
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date
from unstructured.partition.utils.config import env_config
from unstructured.telemetry import partition_runtime_telemetry
from unstructured.utils import is_temp_file_path

DETECTION_ORIGIN: str = "csv"
CSV_FIELD_LIMIT = 10 * 1048576  # 10MiB


@partition_runtime_telemetry("csv")
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

    csv.field_size_limit(CSV_FIELD_LIMIT)
    with ctx.open() as file:
        check_cell_count(file, ctx.delimiter, ctx.encoding)
    with ctx.open() as file:
        read_kw: dict = {"header": ctx.header, "sep": ctx.delimiter, "encoding": ctx.encoding}
        # sep=None is not supported by the C engine; use Python engine to avoid ParserWarning.
        if ctx.delimiter is None:
            read_kw["engine"] = "python"
        dataframe = pd.read_csv(file, **read_kw)

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


def check_cell_count(file: IO[bytes], delimiter: str | None, encoding: str | None) -> None:
    """Raise `UnprocessableEntityError` when `file` would span more than `CSV_MAX_CELLS` cells.

    Pandas sizes the data-frame by the first record and pads every shorter record out to that
    width, so a tiny file whose first line is a long run of delimiters can span millions of cells.
    The span is measured here by streaming the records, before Pandas allocates anything, and the
    scan stops as soon as the limit is passed. `file` is read from its current position.
    """
    max_cells = env_config.CSV_MAX_CELLS
    # -- `errors="replace"` so the scan never fails on a file Pandas would read --
    lines: Iterator[str] = codecs.getreader(encoding or "utf-8")(file, errors="replace")

    if delimiter is None:
        # -- With `sep=None` Pandas sniffs the delimiter itself, from the first non-blank line
        # -- and without restricting the candidates, so measure with the delimiter it will use.
        first_line = next((line for line in lines if line.strip()), "")
        try:
            delimiter = csv.Sniffer().sniff(first_line).delimiter
        except csv.Error:
            delimiter = None
        lines = itertools.chain([first_line], lines)

    # -- a single-column file has no delimiter; any character absent from each line will do --
    records = csv.reader(lines, delimiter=delimiter or "\n")

    n_rows, n_cols = 0, 0
    for record in records:
        if not record:  # -- Pandas skips blank lines --
            continue
        if n_rows == 0:
            n_cols = len(record)
        n_rows += 1
        if n_rows * n_cols > max_cells:
            raise UnprocessableEntityError(
                f"File exceeds the maximum of {max_cells:,} table cells (CSV_MAX_CELLS): it spans"
                f" at least {n_rows:,} rows x {n_cols:,} columns."
            )


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

    @cached_property
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
            return sniffer.sniff(data, delimiters=",;|").delimiter
        except csv.Error:
            # -- sniffing will fail on single-column csv as no default can be assumed --
            return None

    @cached_property
    def header(self) -> int | None:
        """Identifies the header row, if any, to Pandas, by idx."""
        return 0 if self._include_header else None

    @cached_property
    def encoding(self) -> str | None:
        """The encoding to use for reading the file."""
        return self._encoding

    @cached_property
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
