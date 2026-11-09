from __future__ import annotations

import codecs
import collections
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
        n_columns = check_cell_count(file, ctx.delimiter, ctx.encoding)
    with ctx.open() as file:
        dataframe = read_delimited_text(
            file,
            sep=ctx.delimiter,
            header=ctx.header,
            encoding=ctx.encoding,
            n_columns=n_columns,
        )

    if not len(dataframe.columns):
        # -- an empty file holds no table --
        return []

    html_table = HtmlTable.from_html_text(dataframe_to_html(dataframe, header=include_header))

    metadata = ElementMetadata(
        filename=filename,
        last_modified=ctx.last_modified,
        text_as_html=html_table.html if infer_table_structure else None,
    )

    # -- a CSV file becomes a single `Table` element --
    return [Table(text=html_table.text, metadata=metadata, detection_origin=DETECTION_ORIGIN)]


def dataframe_to_html(dataframe: pd.DataFrame, *, header: bool) -> str:
    """HTML table of `dataframe` with the text of each cell as read and empty cells left empty.

    By default `DataFrame.to_html()` writes a line break or tab inside a cell as its escape
    sequence, so a quoted multi-line CSV field comes out as the literal text `line1\\nline2`.
    A formatter for each column makes Pandas write the cell text itself, still HTML-escaped.
    """
    formatters = {
        col: (lambda value: "" if pd.isna(value) else str(value)) for col in dataframe.columns
    }
    return dataframe.to_html(index=False, header=header, na_rep="", formatters=formatters)  # pyright: ignore


def read_delimited_text(
    file: IO[bytes],
    *,
    sep: str | None,
    header: int | None,
    encoding: str | None,
    n_columns: int | None = None,
) -> pd.DataFrame:
    """Read delimited text from `file` into a data-frame, with each lone "\r" made a "\n".

    Pandas 2.x's C tokenizer mishandles a lone "\r" line ending followed by a whitespace-only line
    while skipping blank lines: it emits 2^18 empty rows for each, so a few bytes become millions
    of rows inside `pd.read_csv()`, before any limit can be checked. Pandas therefore reads the
    file through `_LoneCarriageReturnReader`, which streams it with each "\r" not followed by "\n"
    converted to "\n". "\r\n" is left alone, so text inside quoted fields of a "\r\n" file is
    unchanged.

    When `sep` is `None` the delimiter is sniffed by `_sniff_delimiter()` from the first non-blank
    line, the same way `check_cell_count()` measures it, rather than leaving Pandas to sniff its
    own.

    `n_columns` is the width `check_cell_count()` measures. Pandas otherwise takes the width of the
    table from its first record (or header): it fails on a later, wider record, and when data rows
    are wider than the header it silently makes their first fields the row index. Given the width,
    every record is read whole and a shorter one is padded with empty cells. A header is then the
    first row, labeled the way Pandas labels a header row.
    """
    reader = _LoneCarriageReturnReader(file, encoding)
    # -- each cell is read as the text the file holds: by default Pandas empties a cell that says
    # -- "N/A", "NULL" or "None", turns a column of whole numbers with one empty cell into floats
    # -- (12 reads "12.0") and drops the leading zeros of a code such as "007" --
    cells_as_written: dict[str, Any] = {"dtype": str, "keep_default_na": False}
    try:
        if sep is None:
            sep = _sniff_delimiter(_normalize_line_endings(reader.peek_first_non_blank_line()))
            # -- the C engine does not sniff, so keep the Python engine this path has always used --
            cells_as_written["engine"] = "python"
        if not n_columns:
            return pd.read_csv(reader, sep=sep, header=header, **cells_as_written)

        # -- no `index_col=False`: with it the Python engine drops the fields of a record wider than
        # -- `names`; without it both engines raise, so a width measured short cannot lose text --
        dataframe = pd.read_csv(
            reader, sep=sep, header=None, names=range(n_columns), **cells_as_written
        )
    except pd.errors.EmptyDataError:
        # -- an empty file, or one of only blank lines, has no columns; the partitioners turn that
        # -- into no elements, the same as partitioning an empty text, markdown or HTML file --
        return pd.DataFrame()
    # -- the Python engine pads a short record with `None`, which `to_html()` writes as "None" --
    dataframe = dataframe.fillna("")
    if header is None:
        return dataframe
    return dataframe.iloc[1:].set_axis(_header_labels(dataframe.iloc[0].tolist(), sep), axis=1)


def _header_labels(cells: list[str], sep: str) -> list[str]:
    """The column labels Pandas reads from a header row of `cells`.

    Pandas labels an empty header cell "Unnamed: <i>" and makes a repeated label unique with a
    ".1", ".2" suffix. The row is written out as one line of delimited text for Pandas to read, so
    the labels match those of reading the file with `header=0`. A column the header row has no
    cell over is labeled like an empty header cell.
    """
    line = io.StringIO()
    csv.writer(line, delimiter=sep, lineterminator="\n").writerow(cells)
    line.seek(0)
    columns = pd.read_csv(line, sep=sep, header=0, nrows=0, dtype=str, keep_default_na=False)
    return [str(label) for label in columns.columns]


def check_cell_count(file: IO[bytes], delimiter: str | None, encoding: str | None) -> int:
    """The number of columns of the table in `file`, which is the field count of its widest record.

    Raises `UnprocessableEntityError` when `file` would span more than `CSV_MAX_CELLS` cells.

    `read_delimited_text()` gives Pandas this width as the column names, so every record is padded
    out to the widest one, and a record wider than the first is read whole rather than failing in
    Pandas or having its first fields made the row index. A tiny file with one long run of
    delimiters can therefore span millions of cells. The span is measured here before Pandas
    allocates anything, reading `file` in fixed-size chunks from its current position, with each
    line ending counted as one "\n", and the scan stops as soon as the limit is passed:

    - columns are the fields of the widest record, each counted with Pandas' quoting rules without
      building the fields;
    - rows are the first record plus the line terminators after it. That is an upper bound, since
      blank lines and newlines inside quoted fields count too, so the scan can over-count but
      never under-count.

    The width is 0 when `file` has no non-blank record.

    This is a conservative estimate of the cells Pandas will build, not a bound on memory or bytes
    read: blank lines held while sniffing, or a stream spooled because it cannot seek, still take
    space in proportion to the input.
    """
    max_cells = env_config.CSV_MAX_CELLS
    chunks = (_normalize_line_endings(c) for c in _iter_decoded_chunks(file, encoding))

    def raise_limit_exceeded(n_rows: int, n_cols: int) -> NoReturn:
        raise UnprocessableEntityError(
            f"File exceeds the maximum of {max_cells:,} table cells (CSV_MAX_CELLS): it spans"
            f" at least {n_rows:,} rows x {n_cols:,} columns."
        )

    # -- with no delimiter given, `read_delimited_text()` sniffs one and uses Pandas' Python
    # -- engine, which skips more kinds of blank line --
    python_engine = delimiter is None
    if delimiter is None:
        first_line, chunks = _peek_first_non_blank_line(chunks)
        delimiter = _sniff_delimiter(first_line)

    n_cols, chunks = _first_record_width(
        chunks, delimiter, python_engine, max_cells, raise_limit_exceeded
    )
    if n_cols == 0:
        return 0
    n_rows = 1

    # -- each later "\n" ends a row, and so does end-of-file when the last line is unterminated --
    widths = _RecordWidths(delimiter)
    unterminated = False
    for chunk in chunks:
        if n_terminators := chunk.count("\n"):
            n_rows += n_terminators
            unterminated = not chunk.endswith("\n")
        elif chunk:
            unterminated = True
        n_cols = max(n_cols, widths.feed(chunk))
        if (n_rows + unterminated) * n_cols > max_cells:
            raise_limit_exceeded(n_rows + unterminated, n_cols)

    return n_cols


# -- the delimiter of a file with no usable one, which is then read as one column. It is the ASCII
# -- "unit separator", so a file that does contain it is split on it, the same way by both
# -- `check_cell_count()` and Pandas --
_ONE_COLUMN_DELIMITER = "\x1f"

_CSV_CHUNK_CHARS = 1 << 16


class _LoneCarriageReturnReader(io.TextIOBase):
    """Text stream of `file`, decoded in chunks, with each "\r" not followed by "\n" made a "\n".

    A "\r" ending a chunk is held back until the next chunk shows whether it starts a "\r\n". The
    file is never held in memory whole: decoded chunks wait in a queue until they are read, and
    only the lines `.peek_first_non_blank_line()` looks past stay queued after it returns.

    Each character is copied a bounded number of times however the text is read, so reading is
    linear in the size of the file; `._chars_copied` counts the copies.
    """

    def __init__(self, file: IO[bytes], encoding: str | None):
        self._file = file
        self._decoder = codecs.getincrementaldecoder(_python_encoding(encoding))()
        self._chunks: collections.deque[str] = collections.deque()
        self._offset = 0  # -- read position in the first queued chunk --
        self._held_cr = False
        self._at_start = True
        self._eof = False
        self._chars_copied = 0

    def peek_first_non_blank_line(self) -> str:
        """The first line that is not blank, or "" if there is none, without consuming it."""
        line_parts: list[str] = []  # -- the current line, kept only until it proves blank --
        idx, start = 0, self._offset
        while True:
            if idx == len(self._chunks):
                if not self._fill():
                    line = self._join(line_parts)
                    return line if line.strip() else ""
                continue
            chunk = self._chunks[idx]
            end = chunk.find("\n", start) + 1 or len(chunk)
            line_parts.append(self._slice(chunk, start, end))
            if not line_parts[-1].isspace() and line_parts[-1]:
                # -- not blank; complete the line, then return it --
                while not line_parts[-1].endswith("\n"):
                    idx, start = idx + 1, 0
                    # -- a fill can queue nothing (e.g. a chunk holding only a held-back "\r") --
                    while idx == len(self._chunks):
                        if not self._fill():
                            return self._join(line_parts)
                    chunk = self._chunks[idx]
                    end = chunk.find("\n") + 1 or len(chunk)
                    line_parts.append(self._slice(chunk, 0, end))
                return self._join(line_parts)
            if line_parts[-1].endswith("\n"):
                line_parts = []
            if end == len(chunk):
                idx, start = idx + 1, 0
            else:
                start = end

    def read(self, size: int | None = -1) -> str:
        parts: list[str] = []
        remaining = -1 if size is None or size < 0 else size
        while remaining != 0 and (self._chunks or self._fill()):
            if not self._chunks:
                continue
            chunk = self._chunks[0]
            end = len(chunk) if remaining < 0 else min(len(chunk), self._offset + remaining)
            parts.append(self._slice(chunk, self._offset, end))
            if remaining > 0:
                remaining -= end - self._offset
            self._advance(end)
        return self._join(parts)

    def readline(self, size: int | None = -1) -> str:
        parts: list[str] = []
        remaining = -1 if size is None or size < 0 else size
        while remaining != 0 and (self._chunks or self._fill()):
            if not self._chunks:
                continue
            chunk = self._chunks[0]
            end = chunk.find("\n", self._offset) + 1 or len(chunk)
            if remaining > 0:
                end = min(end, self._offset + remaining)
                remaining -= end - self._offset
            parts.append(self._slice(chunk, self._offset, end))
            self._advance(end)
            if parts[-1].endswith("\n"):
                break
        return self._join(parts)

    def readable(self) -> bool:
        return True

    def _advance(self, end: int) -> None:
        """Move the read position to `end` in the first queued chunk, dropping it once read."""
        if end == len(self._chunks[0]):
            self._chunks.popleft()
            self._offset = 0
        else:
            self._offset = end

    def _fill(self) -> bool:
        """Queue the next decoded chunk; False when the file is exhausted."""
        if self._eof:
            return False
        chunk = self._file.read(_CSV_CHUNK_CHARS)
        text = self._decoder.decode(chunk, final=not chunk)
        if self._at_start:
            text, self._at_start = _strip_leading_bom(text)
        if self._held_cr:
            text = "\r" + text
            self._held_cr = False
        if not chunk:
            self._eof = True
        elif text.endswith("\r"):
            text, self._held_cr = text[:-1], True
        if text:
            self._chunks.append(_LONE_CARRIAGE_RETURN.sub("\n", text))
        return True

    def _join(self, parts: list[str]) -> str:
        if len(parts) == 1:
            return parts[0]
        self._chars_copied += sum(map(len, parts))
        return "".join(parts)

    def _slice(self, chunk: str, start: int, end: int) -> str:
        if start == 0 and end == len(chunk):
            return chunk
        self._chars_copied += end - start
        return chunk[start:end]


_LONE_CARRIAGE_RETURN = re.compile("\r(?!\n)")


def _python_encoding(encoding: str | None) -> str:
    """The codec to decode with: `encoding`, or UTF-8, dropping a UTF-8 byte-order mark as Pandas
    does."""
    encoding = encoding or "utf-8"
    return "utf-8-sig" if codecs.lookup(encoding).name == "utf-8" else encoding


def _strip_leading_bom(text: str) -> tuple[str, bool]:
    """`text` without leading byte-order marks, and whether the start of the file is still ahead.

    Pandas drops a byte-order mark from the start of the text it is given, so every leading one is
    dropped before Pandas or the scan sees the text, leaving none for Pandas to drop differently.
    """
    text = text.lstrip("\ufeff")
    return text, not text


def _normalize_line_endings(text: str) -> str:
    """`text` with each "\r\n" and "\r" line ending replaced by "\n".

    Applied chunk by chunk, a "\r\n" split across chunks becomes two line endings, which only adds
    a blank line.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _sniff_delimiter(first_line: str) -> str:
    """The delimiter `csv.Sniffer` finds in `first_line`, or `_ONE_COLUMN_DELIMITER`."""
    try:
        delimiter = csv.Sniffer().sniff(first_line).delimiter
    except csv.Error:
        return _ONE_COLUMN_DELIMITER
    # -- a quote or line ending cannot delimit fields --
    return _ONE_COLUMN_DELIMITER if delimiter in ('"', "\n", "\r") else delimiter


def _iter_decoded_chunks(file: IO[bytes], encoding: str | None) -> Iterator[str]:
    """Generate the text of `file` in chunks of up to `_CSV_CHUNK_CHARS` bytes, decoded."""
    # -- `errors="replace"` so the scan never fails on a file Pandas would read --
    decoder = codecs.getincrementaldecoder(_python_encoding(encoding))(errors="replace")
    at_start = True
    while chunk := file.read(_CSV_CHUNK_CHARS):
        text = decoder.decode(chunk)
        if at_start:
            text, at_start = _strip_leading_bom(text)
        if text:
            yield text
    if text := decoder.decode(b"", final=True):
        yield text.lstrip("\ufeff") if at_start else text


def _peek_first_non_blank_line(chunks: Iterator[str]) -> tuple[str, Iterator[str]]:
    """The first line of `chunks` that is not blank, and all of `chunks`, that line included.

    The line ends with its "\n"; it is "" when every line is blank. Each chunk read is queued
    unchanged for the returned chunks, and only the non-blank line itself is copied.
    """
    read: list[str] = []
    line_parts: list[str] = []  # -- the current line, kept only until it proves blank --
    for chunk in chunks:
        read.append(chunk)
        start = 0
        while start < len(chunk):
            end = chunk.find("\n", start) + 1 or len(chunk)
            segment = chunk[start:end]
            line_parts.append(segment)
            if segment and not segment.isspace():
                if not segment.endswith("\n"):
                    # -- complete the line from the chunks that follow --
                    for more in chunks:
                        read.append(more)
                        end = more.find("\n") + 1 or len(more)
                        line_parts.append(more[:end])
                        if line_parts[-1].endswith("\n"):
                            break
                return "".join(line_parts), itertools.chain(read, chunks)
            if segment.endswith("\n"):
                line_parts = []
            start = end
    line = "".join(line_parts)
    return (line if line.strip() else ""), iter(read)


def _first_record_width(
    chunks: Iterator[str],
    delimiter: str,
    python_engine: bool,
    max_cells: int,
    raise_limit_exceeded: Callable[[int, int], NoReturn],
) -> tuple[int, Iterator[str]]:
    """The field count of the first non-blank record, and the chunks that follow it.

    Follows the quoting rules Pandas applies by default: a `"` opens a quoted field only at the
    start of a field, `""` inside a quoted field is a literal quote, and delimiters and newlines
    inside a quoted field are part of the field. A record with no delimiter is blank when Pandas
    skips it: for its C engine when it has no quote and only spaces and tabs; for its Python engine
    when its one field's value, quoted or not, is empty or only `str.isspace()` characters. The
    count is 0 when there is no non-blank record. The limit is applied to the record alone.
    """
    is_blank = str.isspace if python_engine else (lambda text: not text.strip(" \t"))
    special = re.compile(f"[{re.escape(delimiter)}\n]")
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
                        has_content = True
                        i += 1
                    else:  # -- the quote closed the quoted part; the field continues --
                        in_quotes = False
                    continue
                j = chunk.find('"', i)
                # -- the Python engine judges blankness by the value, quoted text included --
                quoted_text = chunk[i:] if j < 0 else chunk[i:j]
                if quoted_text and not quoted_text.isspace():
                    has_content = True
                if j < 0:
                    break
                quote_pending, i = True, j + 1
                continue

            if at_field_start and chunk[i] == '"':
                # -- a quote alone makes a record non-blank for the C engine, which skips blank
                # -- lines before parsing quotes --
                in_quotes, at_field_start = True, False
                has_content = has_content or not python_engine
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


class _RecordWidths:
    """The field count of the widest record in text fed to it chunk by chunk.

    Starts at the beginning of a record and follows the quoting rules of `_first_record_width()`:
    a `"` opens a quoted field only at the start of a field, `""` inside a quoted field is a
    literal quote, and delimiters and newlines inside a quoted field are part of the field. Blank
    lines need no rule of their own: a blank line is one field, which is never wider than the
    first, non-blank, record.

    Text outside quotes is measured a line at a time with `str.count()`, so the scan takes a step
    for each line and each quote rather than for each field.
    """

    def __init__(self, delimiter: str):
        self._delimiter = delimiter
        self._widest = 0
        self._n_delimiters = 0  # -- in the record being read --
        self._at_field_start = True
        self._in_quotes = False
        self._quote_pending = False  # -- a `"` in a quoted field, which may begin a `""` --

    def feed(self, chunk: str) -> int:
        """Scan `chunk`; the widest record so far, the one not yet ended included."""
        delimiter, widest, n_delimiters = self._delimiter, self._widest, self._n_delimiters
        at_field_start, in_quotes = self._at_field_start, self._in_quotes
        i, n = 0, len(chunk)
        if self._quote_pending and n:
            # -- the previous chunk ended with a quote inside a quoted field --
            self._quote_pending = False
            if chunk[0] == '"':  # -- `""` is a literal quote --
                i = 1
            else:  # -- the quote closed the quoted part; the field continues --
                in_quotes = False

        while i < n:
            if in_quotes:
                j = chunk.find('"', i)
                if j < 0:
                    break
                if j + 1 == n:  # -- whether it begins a `""` is up to the next chunk --
                    self._quote_pending = True
                    break
                if chunk[j + 1] == '"':  # -- `""` is a literal quote --
                    i = j + 2
                else:  # -- the quote closed the quoted part; the field continues --
                    in_quotes, i = False, j + 1
                continue

            # -- unquoted text runs to the next quote; each "\n" in it ends a record --
            quote = chunk.find('"', i)
            end = n if quote < 0 else quote
            while (newline := chunk.find("\n", i, end)) >= 0:
                widest = max(widest, n_delimiters + chunk.count(delimiter, i, newline) + 1)
                n_delimiters, at_field_start = 0, True
                i = newline + 1
            if i < end:
                n_delimiters += chunk.count(delimiter, i, end)
                at_field_start = chunk[end - 1] == delimiter
                i = end
            if quote >= 0:  # -- a quote anywhere but at the start of a field is literal text --
                in_quotes, at_field_start = at_field_start, False
                i = quote + 1

        self._widest, self._n_delimiters = widest, n_delimiters
        self._at_field_start, self._in_quotes = at_field_start, in_quotes
        return max(widest, n_delimiters + 1)


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
