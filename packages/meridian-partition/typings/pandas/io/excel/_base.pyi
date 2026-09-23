from __future__ import annotations

from typing import Sequence

from pandas._typing import FilePath, ReadBuffer
from pandas.core.frame import DataFrame

def read_excel(
    io: FilePath | ReadBuffer[bytes],
    sheet_name: None,
    *,
    header: int | Sequence[int] | None = ...,
) -> dict[str, DataFrame]: ...
