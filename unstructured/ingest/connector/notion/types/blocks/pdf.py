# https://developers.notion.com/reference/block#pdf
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.attributes import Href
from htmlBuilder.tags import A, Br, Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.file import External, File
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class PDF(BlockBase):
    type: str
    caption: List[RichText] = field(default_factory=list)
    external: Optional[External] = None
    file: Optional[File] = None

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        caption = data.pop("caption", [])
        t = data["type"]
        paragraph = cls(type=t)
        paragraph.caption = [RichText.from_dict(c) for c in caption]
        if t == "external":
            paragraph.external = External.from_dict(data["external"])
        elif t == "file":
            paragraph.file = File.from_dict(data["file"])
        return paragraph

    def get_html(self) -> Optional[HtmlTag]:
        texts = []
        if self.external:
            texts.append(A([Href(self.external.url)], self.external.url))
        if self.file:
            texts.append(A([Href(self.file.url)], self.file.url))
        if self.caption:
            texts.append(Div([], [rt.get_html() for rt in self.caption]))
        if not texts:
            return None
        joined = [Br()] * (len(texts) * 2 - 1)
        joined[0::2] = texts

        return Div([], joined)
