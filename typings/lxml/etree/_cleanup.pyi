# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import Collection, overload

from .._types import _ElementOrTree, _TagSelector

@overload
def strip_elements(
    __tree_or_elem: _ElementOrTree,
    *tag_names: _TagSelector,
    with_tail: bool = True,
) -> None: ...
@overload
def strip_elements(
    __tree_or_elem: _ElementOrTree,
    __tag: Collection[_TagSelector],
    /,
    with_tail: bool = True,
) -> None: ...
