from __future__ import annotations

from typing import IO, Literal

from pandas.core.frame import DataFrame

def read_csv(
    filepath_or_buffer: str | IO[bytes],
    *,
    encoding: str | None = ...,
    sep: str | None = ...,
    header: int | None | Literal["infer"] = ...,
) -> DataFrame: ...
