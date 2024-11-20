from __future__ import annotations

import pathlib
from typing import IO

def guess_mime(obj: bytearray | str | bytes | pathlib.PurePath | IO[bytes]) -> str | None: ...
