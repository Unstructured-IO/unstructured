# pyright: reportPrivateUsage=false

from __future__ import annotations

from lxml.html._element import HtmlElement

def fromstring(
    data: str,
) -> HtmlElement: ...
