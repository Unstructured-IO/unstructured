from __future__ import annotations

import codecs
import contextlib
import csv
import io
import itertools
import re
from functools import cached_property
from typing import IO, Any, Callable, Iterator, NoReturn

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
        dataframe = read_delimited_text(
            file, sep=ctx.delimiter, header=ctx.header, encoding=ctx.encoding
        )

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


def read_delimited_text(
    file: IO[bytes], *, sep: str | None, header: int | None, encoding: str | None
) -> pd.DataFrame:
    """Read delimited text from `file` into a data-frame, with its line endings normalized.

    Pandas 2.x's C tokenizer mishandles a "\r" line ending followed by a whitespace-only line
    while skipping blank lines: it emits 2^18 empty rows for each, so a few bytes become millions
    of rows inside `pd.read_csv()`, before any limit can be checked. Every line ending is therefore
    converted to "\n" (including inside quoted fields) and given to Pandas as its only terminator.

    When `sep` is `None` the delimiter is sniffed from the first line by `_sniff_delimiter()`, the
    same way `check_cell_count()` measures it, rather than leaving Pandas to sniff its own.
    """
    encoding = encoding or "utf-8"
    # -- like Pandas, drop a UTF-8 byte-order mark --
    if codecs.lookup(encoding).name == "utf-8":
        encoding = "utf-8-sig"
    text = _normalize_line_endings(file.read().decode(encoding))

    if sep is None:
        sep = _sniff_delimiter(text[: text.find("\n") + 1] if "\n" in text else text)
        if sep is None:
            # -- no usable delimiter, so the file is one column; split on a character it lacks --
            sep = next((c for c in _ABSENT_DELIMITER_CANDIDATES if c not in text), None)
            if sep is None:
                raise UnprocessableEntityError("Could not determine the delimiter of the file.")
        # -- the C engine does not sniff and the Python engine needs no custom line terminator,
        # -- so keep the Python engine this path has always used --
        return pd.read_csv(io.StringIO(text), sep=sep, header=header, engine="python")
    return pd.read_csv(io.StringIO(text), sep=sep, header=header, lineterminator="\n")


def check_cell_count(file: IO[bytes], delimiter: str | None, encoding: str | None) -> None:
    """Raise `UnprocessableEntityError` when `file` would span more than `CSV_MAX_CELLS` cells.

    Pandas sizes the data-frame by the first record and pads every shorter record out to that
    width, so a tiny file whose first line is a long run of delimiters can span millions of cells.
    The span is measured here before Pandas allocates anything, reading `file` in fixed-size chunks
    from its current position, with line endings normalized as `read_delimited_text()` does, and
    the scan stops as soon as the limit is passed:

    - columns are the fields of the first record, counted with Pandas' quoting rules without
      building the fields;
    - rows are counted as line terminators after it. That is an upper bound, since blank lines and
      newlines inside quoted fields count too, so the scan can over-count but never under-count.
    """
    max_cells = env_config.CSV_MAX_CELLS
    chunks = (_normalize_line_endings(c) for c in _iter_decoded_chunks(file, encoding or "utf-8"))

    def raise_limit_exceeded(n_rows: int, n_cols: int) -> NoReturn:
        raise UnprocessableEntityError(
            f"File exceeds the maximum of {max_cells:,} table cells (CSV_MAX_CELLS): it spans"
            f" at least {n_rows:,} rows x {n_cols:,} columns."
        )

    # -- with no delimiter given, `read_delimited_text()` sniffs one and uses Pandas' Python
    # -- engine, which skips more kinds of blank line --
    python_engine = delimiter is None
    if delimiter is None:
        first_line, chunks = _split_first_line(chunks)
        # -- `None` when the file is read as one column --
        delimiter = _sniff_delimiter(first_line)
        chunks = itertools.chain([first_line], chunks)

    n_cols, chunks = _first_record_width(
        chunks, delimiter, python_engine, max_cells, raise_limit_exceeded
    )
    if n_cols == 0:
        return

    # -- the first record is row 1; each later "\n" ends a row, and so does end-of-file when the
    # -- last line is unterminated --
    n_rows, unterminated = 1, False
    for chunk in chunks:
        if n_terminators := chunk.count("\n"):
            n_rows += n_terminators
            unterminated = not chunk.endswith("\n")
        elif chunk:
            unterminated = True
        if (n_rows + unterminated) * n_cols > max_cells:
            raise_limit_exceeded(n_rows + unterminated, n_cols)


# -- characters `read_delimited_text()` may split a one-column file on, if absent from it --
_ABSENT_DELIMITER_CANDIDATES = "\x1f\x1e\x1d\x1c\x07\x08"

_CSV_CHUNK_CHARS = 1 << 16


def _normalize_line_endings(text: str) -> str:
    """`text` with each "\r\n" and "\r" line ending replaced by "\n".

    Applied chunk by chunk, a "\r\n" split across chunks becomes two line endings, which only adds
    a blank line.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _sniff_delimiter(first_line: str) -> str | None:
    """The delimiter `csv.Sniffer` finds in `first_line`, or `None` when there is no usable one."""
    try:
        delimiter = csv.Sniffer().sniff(first_line).delimiter
    except csv.Error:
        return None
    # -- a quote or line ending cannot delimit fields --
    return None if delimiter in ('"', "\n", "\r") else delimiter


def _iter_decoded_chunks(file: IO[bytes], encoding: str) -> Iterator[str]:
    """Generate the text of `file` in chunks of up to `_CSV_CHUNK_CHARS` bytes, decoded."""
    # -- `errors="replace"` so the scan never fails on a file Pandas would read --
    decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
    while chunk := file.read(_CSV_CHUNK_CHARS):
        if text := decoder.decode(chunk):
            yield text
    if text := decoder.decode(b"", final=True):
        yield text


def _split_first_line(chunks: Iterator[str]) -> tuple[str, Iterator[str]]:
    """The first line of `chunks` with its "\n", and the chunks that follow it."""
    pending = ""
    for chunk in chunks:
        pending += chunk
        if (end := pending.find("\n") + 1) > 0:
            return pending[:end], itertools.chain([pending[end:]], chunks)
    return pending, iter(())


def _first_record_width(
    chunks: Iterator[str],
    delimiter: str | None,
    python_engine: bool,
    max_cells: int,
    raise_limit_exceeded: Callable[[int, int], NoReturn],
) -> tuple[int, Iterator[str]]:
    """The field count of the first non-blank record, and the chunks that follow it.

    Follows the quoting rules Pandas applies by default: a `"` opens a quoted field only at the
    start of a field, `""` inside a quoted field is a literal quote, and delimiters and newlines
    inside a quoted field are part of the field. A record with no delimiter or quote and only
    whitespace is blank, as Pandas skips it: spaces and tabs for its C engine, anything
    `str.isspace()` for its Python engine. A `None` delimiter means a one-column file. The count is
    0 when there is no non-blank record. The limit is applied to the record alone.
    """
    is_blank = str.isspace if python_engine else (lambda text: not text.strip(" \t"))
    special = re.compile(f"[{re.escape(delimiter)}\n]" if delimiter else "\n")
    in_quotes = quote_pending = has_content = False
    at_field_start = True
    n_delimiters = 0

    for chunk in chunks:
        i, n = 0, len(chunk)
        while i < n:
            if in_quotes:
                if quote_pending:
                    quote_pending = False
                    if chunk[i] == '"':  # -- `""` is a literal quote --
                        i += 1
                    else:  # -- the quote closed the quoted part; the field continues --
                        in_quotes = False
                    continue
                j = chunk.find('"', i)
                if j < 0:
                    break
                quote_pending, i = True, j + 1
                continue

            if at_field_start and chunk[i] == '"':
                in_quotes = has_content = True
                at_field_start = False
                i += 1
                continue

            match = special.search(chunk, i)
            j = match.start() if match else n
            if j > i:
                at_field_start = False
                has_content = has_content or not is_blank(chunk[i:j])
            if match is None:
                break
            i = j + 1
            if chunk[j] == delimiter:
                n_delimiters += 1
                has_content = at_field_start = True
                if n_delimiters + 1 > max_cells:
                    raise_limit_exceeded(1, n_delimiters + 1)
            elif has_content:  # -- end of the first record --
                if n_delimiters + 1 > max_cells:
                    raise_limit_exceeded(1, n_delimiters + 1)
                return n_delimiters + 1, itertools.chain([chunk[i:]], chunks)
            else:  # -- a blank line, which Pandas skips --
                at_field_start = True

    if not has_content:
        return 0, iter(())
    if n_delimiters + 1 > max_cells:
        raise_limit_exceeded(1, n_delimiters + 1)
    return n_delimiters + 1, iter(())


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
