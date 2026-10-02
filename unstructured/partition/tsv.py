from __future__ import annotations

import contextlib
import shutil
import tempfile
from typing import IO, Any, Iterator, Optional, cast

from pandas.io.common import get_handle

from unstructured.chunking import add_chunking_strategy
from unstructured.common.html_table import HtmlTable
from unstructured.documents.elements import Element, ElementMetadata, Table
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import (
    exactly_one,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date
from unstructured.partition.csv import check_cell_count, read_delimited_text
from unstructured.telemetry import partition_runtime_telemetry

DETECTION_ORIGIN: str = "tsv"


@partition_runtime_telemetry("tsv")
@apply_metadata(FileType.TSV)
@add_chunking_strategy
def partition_tsv(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    include_header: bool = False,
    **kwargs: Any,
) -> list[Element]:
    """Partitions TSV files into document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_header
        Determines whether or not header info info is included in text and medatada.text_as_html.
    """
    exactly_one(filename=filename, file=file)

    header = 0 if include_header else None

    if filename:
        # -- like `pd.read_csv(filename)`, decompress a file named e.g. "x.tsv.gz"; the size check
        # -- and the read each get their own decompressing handle on the same content --
        with _open_decompressed(filename) as f:
            check_cell_count(f, "\t", None, header=include_header)
        with _open_decompressed(filename) as f:
            dataframe = read_delimited_text(f, sep="\t", header=header, encoding=None)
    else:
        assert file is not None
        # -- Note(scanny): `SpooledTemporaryFile` on Python<3.11 does not implement `.readable()`
        # -- which triggers an exception on `pd.DataFrame.read_csv()` call.
        f = spooled_to_bytes_io_if_needed(file)
        with _rereadable(f) as f:
            start = f.tell()
            check_cell_count(f, "\t", None, header=include_header)
            f.seek(start)
            dataframe = read_delimited_text(f, sep="\t", header=header, encoding=None)

    html_table = HtmlTable.from_html_text(
        dataframe.to_html(index=False, header=include_header, na_rep="")
    )

    metadata = ElementMetadata(
        filename=filename,
        last_modified=get_last_modified_date(filename) if filename else None,
        text_as_html=html_table.html,
    )
    metadata.detection_origin = DETECTION_ORIGIN

    return [Table(text=html_table.text, metadata=metadata)]


@contextlib.contextmanager
def _open_decompressed(filename: str) -> Iterator[IO[bytes]]:
    """Open `filename` for reading bytes, decompressed as its extension (e.g. ".gz") implies."""
    with get_handle(filename, "rb", compression="infer", is_text=False) as handles:
        yield cast(IO[bytes], handles.handle)


@contextlib.contextmanager
def _rereadable(file: IO[bytes]) -> Iterator[IO[bytes]]:
    """`file` itself if it can seek, otherwise a spooled copy of the rest of it.

    The size check and the read each read the file, so a stream that cannot seek back (e.g. a
    pipe or socket) is copied once to a temporary file, which spills to disk when large.
    """
    try:
        seekable = file.seekable()
    except (AttributeError, ValueError):
        seekable = False
    if seekable:
        yield file
        return
    with tempfile.SpooledTemporaryFile(max_size=_SPOOL_MAX_MEMORY_BYTES) as copy:
        shutil.copyfileobj(file, copy)
        copy.seek(0)
        yield cast(IO[bytes], copy)


_SPOOL_MAX_MEMORY_BYTES = 64 * 1024 * 1024
