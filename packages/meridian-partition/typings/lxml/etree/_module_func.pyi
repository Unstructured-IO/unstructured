# pyright: reportPrivateUsage=false

from __future__ import annotations

from .._types import _ElementOrTree
from ..etree import HTMLParser, XMLParser
from ._element import _Element

def fromstring(text: str | bytes, parser: XMLParser | HTMLParser) -> _Element: ...

# Under XML Canonicalization (C14N) mode, most arguments are ignored,
# some arguments would even raise exception outright if specified.
def tostring(
    element_or_tree: _ElementOrTree,
    *,
    encoding: str | type[str] | None = None,
    pretty_print: bool = False,
    with_tail: bool = True,
) -> str: ...
