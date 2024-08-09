# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING

from .._types import _DefEtreeParsers
from ._element import HtmlElement

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

_HtmlElemParser: TypeAlias = _DefEtreeParsers[HtmlElement]

def fragment_fromstring(
    html: str,
    create_parent: bool = False,
    base_url: str | None = None,
    parser: _HtmlElemParser | None = None,
) -> HtmlElement: ...
