from __future__ import annotations

from .. import etree

class HtmlElement(etree.ElementBase):
    def text_content(self) -> str: ...
