# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import Any

from .._types import _ElementOrTree

class XPath:
    def __init__(self, path: str) -> None: ...
    def __call__(self, _etree_or_element: _ElementOrTree) -> Any: ...
    @property
    def path(self) -> str: ...
